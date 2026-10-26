"""Collect observed unittest lifecycle events or import JUnit, without guessing stages."""
import contextlib
import inspect
import io
import json
import os
import platform
import sys
import time
import traceback
import unittest
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

OUTCOMES = ("passed","failed","error","skipped","expected_failure","unexpected_success","interrupted")
BAD = {"failed","error","unexpected_success","interrupted"}
STAGES = ("discovery","fixture_setup","setup","test","teardown","cleanup","fixture_teardown","unknown")


def failure(err, stage, kind):
    frames=[{"file":f.filename,"line":f.lineno,"function":f.name} for f in traceback.extract_tb(err[2])]
    return {"stage":stage,"kind":kind,"message":str(err[1]),"traceback":''.join(traceback.format_exception(*err)),"frames":frames}


class ObservedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.records=[];self.by_test={};self.origin=time.perf_counter()

    def record(self,test):
        key=id(test)
        if key not in self.by_test:
            name=test.id();kind="test"
            if type(test).__name__=='_ErrorHolder':kind='fixture'
            if type(test).__name__=='_FailedTest':kind='discovery'
            record={"id":name,"suite":'.'.join(name.split('.')[:-1]) or name,"kind":kind,"outcome":"interrupted",
                    "duration_s":None,"events":[],"failures":[],"subtests":[],"skip_reason":None}
            self.by_test[key]=record;self.records.append(record)
        return self.by_test[key]

    def startTest(self,test):
        super().startTest(test);self.record(test)["started"]=time.perf_counter()

    def stopTest(self,test):
        record=self.record(test);record['duration_s']=time.perf_counter()-record.pop('started',time.perf_counter())
        super().stopTest(test)

    def stage(self,test,err):
        record=self.record(test)
        if record['kind']=='discovery':return 'discovery'
        for frame in reversed(traceback.extract_tb(err[2])):
            if frame.name in {'setUpClass','setUpModule'}:return 'fixture_setup'
            if frame.name in {'tearDownClass','tearDownModule'}:return 'fixture_teardown'
        failed=[e for e in record['events'] if e['outcome'] in {'failed','error'}]
        return getattr(test,'_observed_stage',None) or (failed[-1]['stage'] if failed else 'unknown')

    def addSuccess(self,test):
        record=self.record(test)
        if not any(s['outcome'] in BAD for s in record['subtests']):record['outcome']='passed'
        super().addSuccess(test)

    def error_record(self,test,err,outcome,kind):
        record=self.record(test);record['outcome']=outcome
        record['failures'].append(failure(err,self.stage(test,err),kind))

    def addFailure(self,test,err):
        self.error_record(test,err,'failed','assertion');super().addFailure(test,err)

    def addError(self,test,err):
        self.error_record(test,err,'error','exception');super().addError(test,err)

    def addSkip(self,test,reason):
        if type(test).__name__=='_SubTest' and getattr(test,'test_case',None) is not None:
            self.record(test.test_case)['subtests'].append({"id":test.id(),"outcome":"skipped","duration_s":None,"skip_reason":reason})
            super().addSkip(test,reason);return
        record=self.record(test);record['outcome']='skipped';record['skip_reason']=reason;super().addSkip(test,reason)

    def addExpectedFailure(self,test,err):
        self.error_record(test,err,'expected_failure','expected assertion');super().addExpectedFailure(test,err)

    def addUnexpectedSuccess(self,test):
        record=self.record(test);record['outcome']='unexpected_success';record['failures'].append({"stage":"test","kind":"unexpected success","message":"Expected failure passed unexpectedly.","traceback":"","frames":[]})
        super().addUnexpectedSuccess(test)

    def addSubTest(self,test,subtest,err):
        record=self.record(test);outcome='passed' if err is None else 'failed' if issubclass(err[0],test.failureException) else 'error'
        child={"id":subtest.id(),"outcome":outcome,"duration_s":None}
        if err:
            detail=failure(err,'test','assertion' if outcome=='failed' else 'exception')
            record['failures'].append(detail);record['outcome']='error' if outcome=='error' or record['outcome']=='error' else 'failed'
            child['failure']=detail
        record['subtests'].append(child);super().addSubTest(test,subtest,err)


def instrument(suite, result_getter):
    for test in suite:
        if isinstance(test,unittest.TestSuite):instrument(test,result_getter);continue
        if type(test).__name__=='_FailedTest':continue
        for name,stage in (('_callSetUp','setup'),('_callTestMethod','test'),('_callTearDown','teardown'),('_callCleanup','cleanup')):
            method=getattr(test,name,None)
            if method is None:continue
            def wrapped(*args,_test=test,_method=method,_stage=stage,**kwargs):
                result=result_getter();record=result.record(_test);started=time.perf_counter()
                event={"stage":_stage,"start_s":started-result.origin,"duration_s":None,"outcome":"passed"};record['events'].append(event)
                previous=getattr(_test,'_observed_stage',None);_test._observed_stage=_stage
                try:
                    value=_method(*args,**kwargs)
                    if _stage=='test' and any(s['outcome'] in BAD for s in record['subtests']):event['outcome']='failed'
                    return value
                except unittest.SkipTest:
                    event['outcome']='skipped';raise
                except BaseException as exc:
                    event['outcome']='failed' if isinstance(exc,AssertionError) else 'error';raise
                finally:
                    event['duration_s']=time.perf_counter()-started;_test._observed_stage=previous
            setattr(test,name,wrapped)


def run_unittest(start,pattern='test*.py',top=None,failfast=False):
    overall=time.perf_counter();loader=unittest.TestLoader();suite=loader.discover(str(start),pattern=pattern,top_level_dir=str(top) if top else None)
    discovered=suite.countTestCases();discovery_duration=time.perf_counter()-overall
    holder={};log=io.StringIO()
    def factory(*args,**kwargs):
        result=ObservedResult(*args,**kwargs);holder['result']=result;return result
    instrument(suite,lambda:holder['result'])
    started=time.perf_counter();interrupted=False
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        try:
            result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=factory,failfast=failfast).run(suite)
        except KeyboardInterrupt:
            interrupted=True;result=holder.get('result')
            if result and result.records and result.records[-1]['outcome']=='interrupted':
                record=result.records[-1];stage=record['events'][-1]['stage'] if record['events'] else 'unknown'
                record['failures'].append(failure(sys.exc_info(),stage,'interrupt'))
    records=result.records if result else []
    for record in records:
        if 'started' in record:record['duration_s']=time.perf_counter()-record.pop('started')
    return {"cases":records,"duration_s":time.perf_counter()-overall,"discovered_tests":discovered,"not_run":max(0,discovered-(result.testsRun if result else 0)),"discovery_duration_s":discovery_duration,"exit_code":130 if interrupted else 0 if result and result.wasSuccessful() and records else 1,
            "runner_tests_run":result.testsRun if result else 0,"runner":"unittest","stage_precision":"instrumented","log":log.getvalue(),
            "runner_error":"Test execution interrupted by KeyboardInterrupt." if interrupted else None,
            "limitations":["Subtest durations are unknown; parent-case timing is observed.","Case timing includes setup, body, teardown, cleanup and framework overhead; stage timings measure the instrumented calls.","Fixture stages are identified only from actual traceback function names; fixture durations are unknown."]}


def import_junit(path):
    raw=Path(path).read_bytes()
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('JUnit external entities/DOCTYPE are not allowed')
    tree=ET.fromstring(raw);records=[];declared=[]
    def visit(node,suite=''):
        tag=node.tag.split('}')[-1]
        if tag=='testsuite':
            suite=node.get('name',suite);declared.append({k:node.get(k) for k in ('name','tests','failures','errors','skipped')})
            direct=[c for c in node if c.tag.split('}')[-1]=='testcase']
            nested=any(c.tag.split('}')[-1]=='testsuite' for c in node)
            if direct and not nested:
                observed={"tests":len(direct),"failures":sum(any(c.tag.split('}')[-1]=='failure' for c in t) for t in direct),"errors":sum(any(c.tag.split('}')[-1]=='error' for c in t) for t in direct),"skipped":sum(any(c.tag.split('}')[-1]=='skipped' for c in t) for t in direct)}
                for key,value in observed.items():
                    if node.get(key) is not None and int(node.get(key))!=value:raise ValueError('JUnit suite totals disagree with case-level records: '+key)
        if tag=='testcase':
            name='.'.join(filter(None,(node.get('classname',suite),node.get('name','unnamed'))))
            try:duration=float(node.get('time')) if node.get('time') is not None else None
            except ValueError:raise ValueError('invalid JUnit duration') from None
            if duration is not None and (not __import__('math').isfinite(duration) or duration<0):raise ValueError('invalid JUnit duration')
            record={"id":name,"suite":node.get('classname',suite) or 'JUnit',"kind":"test","outcome":"passed","duration_s":duration,"events":[],"failures":[],"subtests":[],"skip_reason":None,
                    "producer_file":node.get('file'),"producer_line":node.get('line')}
            for child in node:
                kind=child.tag.split('}')[-1]
                if kind in {'failure','error'}:
                    record['outcome']='error' if kind=='error' else 'failed'
                    record['failures'].append({"stage":"unknown","kind":child.get('type',kind),"message":child.get('message',''),"traceback":child.text or '',"frames":[]})
                elif kind=='skipped':record['skip_reason']=child.get('message',child.text or '')
            kinds={c.tag.split('}')[-1] for c in node}
            if 'skipped' in kinds and kinds & {'failure','error'}:raise ValueError('JUnit case cannot be both skipped and failed')
            if 'error' in kinds:record['outcome']='error'
            elif 'failure' in kinds:record['outcome']='failed'
            elif 'skipped' in kinds:record['outcome']='skipped'
            records.append(record)
        else:
            for child in node:visit(child,suite)
    visit(tree)
    if not records:raise ValueError('JUnit contains no case-level results; suite totals alone cannot locate failed tests')
    return {"cases":records,"runner":"junit","stage_precision":"unknown","duration_s":None,
            "runner_tests_run":len(records),"exit_code":int(any(r['outcome'] in BAD for r in records)),"producer_totals":declared,
            "limitations":["JUnit does not identify setup/test/teardown stage; failure stage remains unknown.","Case time is producer-reported and may include setup/teardown; it is not runner wall time."]}


def coverage_data(path):
    data=json.loads(Path(path).read_text());rows=[]
    def row(name,summary):
        covered,total=summary['covered_lines'],summary['num_statements']
        if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in (covered,total)) or covered>total:raise ValueError('invalid statement coverage counts')
        result={"file":name,"covered":covered,"statements":total,"percent":100*covered/total if total else None}
        if 'num_branches' in summary:
            count,hit=summary['num_branches'],summary['covered_branches']
            if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in (count,hit)) or hit>count:raise ValueError('invalid branch coverage counts')
            result.update(branches=count,covered_branches=hit,branch_percent=100*hit/count if count else None)
        return result
    for name,values in data.get('files',{}).items():rows.append(row(name,values['summary']))
    return {"totals":row('TOTAL',data['totals']),"files":rows,"source_format":"coverage.py JSON"}


def summarize(result):
    counts=Counter(c['outcome'] for c in result['cases'])
    for key in OUTCOMES:counts.setdefault(key,0)
    cases=[c for c in result['cases'] if c['kind']=='test']
    denominator=sum(c['outcome'] in {'passed','failed','error','unexpected_success'} for c in cases)
    passed=sum(c['outcome']=='passed' for c in cases)
    return {"outcomes":dict(counts),"records":len(result['cases']),"test_cases":len(cases),"fixture_records":sum(c['kind']=='fixture' for c in result['cases']),
            "discovery_records":sum(c['kind']=='discovery' for c in result['cases']),"subtests":sum(len(c.get('subtests',[])) for c in cases),
            "pass_rate":100*passed/denominator if denominator else None,"pass_rate_denominator":denominator,
            "pass_rate_definition":"passed / (passed + failed + error + unexpected_success) test cases; skipped and expected failures excluded"}
