"""Task-title identity and status compatibility; run from a documented project root."""
import tempfile
import unittest
from pathlib import Path

from docs_lib import parse_tasks, parse_tasks_detailed, status_rows_html, counts
from integration_core import tasks as mapped_tasks


class TaskNamingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root/'project/phases/phase-2/tasks.md'
        self.path.parent.mkdir(parents=True)

    def test_compact_and_spaced_topics_keep_same_number_title_and_uid(self):
        for separator in ['', ' ', '  ']:
            with self.subTest(separator=separator):
                self.path.write_text('## Experiments\n\n### [ ] 2.6'+separator+'[Agent with Azure MCP] เตรียม Azure MCP\n\n**Task UID:** stable-azure\n**ADO:** #987\n- [ ] Verify the actual approved scope.\n')
                simple = parse_tasks(self.path)[0]
                detailed = parse_tasks_detailed(self.path)[0]
                self.assertEqual(simple['id'], '2.6')
                self.assertEqual(simple['title'], '[Agent with Azure MCP] เตรียม Azure MCP')
                self.assertEqual(detailed['uid'], 'stable-azure')
                self.assertEqual(detailed['id'], simple['id'])
                self.assertEqual(detailed['subtasks'][0]['mark'], ' ')
                mapping = mapped_tasks(self.root)[0]
                self.assertEqual(mapping['uid'], 'stable-azure')
                self.assertIn('**ADO:** #987', mapping['body'])
                self.assertIn('2.6 [Agent with Azure MCP]', status_rows_html([simple]))

    def test_legacy_titles_and_ambiguous_numeric_words_are_preserved(self):
        self.path.write_text('### [x] 2.1 Existing task\n### [/] 2.10.3 Nested task\n### [ ] 2.6Agent is a product name\n### [ ] A task without number\n')
        items = parse_tasks(self.path)
        self.assertEqual([i['id'] for i in items], ['2.1','2.10.3','',''])
        self.assertEqual(items[2]['title'], '2.6Agent is a product name')
        self.assertEqual([i['mark'] for i in items], ['x','/',' ',' '])

    def test_regrouping_does_not_reassign_ids_or_make_exclusions_done(self):
        self.path.write_text('''## PoC

### [x] 2.6 [Schema] Define knowledge tools
**Task UID:** stable-schema
- [x] Verified schema evidence.

## Experiments

### [!] 2.21[Agent with Azure MCP] Investigate Azure MCP (IMP-001)
**Task UID:** stable-azure
**Scope disposition:** out-of-scope; decision recorded separately
- [ ] Implementation not performed.
''')
        items = parse_tasks_detailed(self.path)
        self.assertEqual([(i['id'],i['uid']) for i in items], [('2.6','stable-schema'),('2.21','stable-azure')])
        self.assertEqual(counts(items)['x'],1)
        self.assertEqual(counts(items)['!'],1)
        self.assertEqual(len(items),2)
        self.assertEqual(items[1]['subtasks'][0]['mark'],' ')
        self.assertIn('2.21 [Agent with Azure MCP]',status_rows_html(items))


if __name__ == '__main__':
    unittest.main()
