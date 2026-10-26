// Native macOS rendering for the project-docs workflow animation.
// Invoked by build-gif.py; requires Swift and AppKit.
import AppKit

let output = CommandLine.arguments[1]
let width = 1280, height = 800
let ink = NSColor(srgbRed: 0.10, green: 0.19, blue: 0.25, alpha: 1)
let teal = NSColor(srgbRed: 0.00, green: 0.43, blue: 0.40, alpha: 1)
let muted = NSColor(srgbRed: 0.39, green: 0.46, blue: 0.49, alpha: 1)
let paper = NSColor(srgbRed: 0.96, green: 0.97, blue: 0.95, alpha: 1)
let line = NSColor(srgbRed: 0.80, green: 0.85, blue: 0.83, alpha: 1)
let amber = NSColor(srgbRed: 0.65, green: 0.36, blue: 0.03, alpha: 1)
let titles = ["Many documents. One consistent story.", "Verify evidence. Update the owner file.", "Sync the blocks derived from the source.", "Run the gate before handing over.", "Find a mismatch? Fix it and check again.", "Hand over results, checks, and limits."]
let descriptions = [
    "Example: a task is complete, but the slides and summaries still show the old status.",
    "tasks.md owns task status. Close a task only when supported by evidence.",
    "Scripts update AUTO blocks. Review the surrounding narrative separately.",
    "Check task status, broken links, stale values, and consistency across documents.",
    "Fix the source and affected documents, then run the gate again.",
    "Report what changed, what was checked, and what remains unchecked."
]

func rect(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat, _ color: NSColor, radius: CGFloat = 0) {
    color.setFill()
    NSBezierPath(roundedRect: NSRect(x: x, y: y, width: w, height: h), xRadius: radius, yRadius: radius).fill()
}
func text(_ value: String, _ x: CGFloat, _ y: CGFloat, _ size: CGFloat, _ color: NSColor = ink, bold: Bool = false, mono: Bool = false) {
    let font = mono ? NSFont.monospacedSystemFont(ofSize: size, weight: bold ? .semibold : .regular) : NSFont.systemFont(ofSize: size, weight: bold ? .semibold : .regular)
    (value as NSString).draw(at: NSPoint(x: x, y: y), withAttributes: [.font: font, .foregroundColor: color])
}
func arrow(_ x1: CGFloat, _ y1: CGFloat, _ x2: CGFloat, _ y2: CGFloat, active: Bool) {
    let path = NSBezierPath()
    path.move(to: NSPoint(x: x1, y: y1)); path.line(to: NSPoint(x: x2, y: y2))
    path.lineWidth = active ? 3 : 2
    (active ? teal : line).setStroke(); path.stroke()
    let angle = atan2(y2-y1, x2-x1)
    let head = NSBezierPath()
    head.move(to: NSPoint(x: x2, y: y2))
    head.line(to: NSPoint(x: x2-12*cos(angle-0.45), y: y2-12*sin(angle-0.45)))
    head.line(to: NSPoint(x: x2-12*cos(angle+0.45), y: y2-12*sin(angle+0.45)))
    head.close(); (active ? teal : line).setFill(); head.fill()
}
func badge(_ value: String, _ x: CGFloat, _ y: CGFloat, good: Bool) {
    let c = good ? teal : amber
    rect(x, y, 104, 31, c.withAlphaComponent(0.10), radius: 6)
    text(value, x+13, y+5, 16, c, bold: true)
}
func doc(_ x: CGFloat, _ y: CGFloat, _ name: String, _ subtitle: String, _ status: String, good: Bool, active: Bool) {
    rect(x, y, 402, 98, active ? teal.withAlphaComponent(0.08) : .white, radius: 12)
    rect(x, y+18, 4, 62, active ? teal : line, radius: 2)
    text(name, x+22, y+52, 21, ink, bold: true, mono: true)
    text(subtitle, x+22, y+19, 18, muted)
    badge(status, x+278, y+17, good: good)
}

try FileManager.default.createDirectory(atPath: output, withIntermediateDirectories: true)
for scene in 0..<6 {
  for tick in 0..<12 {
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    let context = NSGraphicsContext(bitmapImageRep: bitmap)!
    NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = context
    context.cgContext.translateBy(x: 0, y: CGFloat(height)); context.cgContext.scaleBy(x: 1, y: -1)
    // Text uses its own upright coordinate transform within the flipped canvas.
    NSGraphicsContext.current = NSGraphicsContext(cgContext: context.cgContext, flipped: true)
    rect(0, 0, 1280, 800, paper)
    rect(0, 0, 12, 800, teal)
    text("project-docs", 52, 28, 34, ink, bold: true, mono: true)
    text("AGENT SKILL / DOCUMENTATION FLOW", 52, 77, 14, muted, mono: true)
    rect(1000, 36, 226, 38, .white, radius: 19)
    text("Illustrative loop", 1020, 43, 18, muted)
    text(titles[scene], 52, 125, 38, ink, bold: true)
    text(descriptions[scene], 52, 187, 23, muted)

    text("SOURCE OF TRUTH", 72, 259, 14, teal, bold: true, mono: true)
    rect(52, 293, 388, 251, .white, radius: 14)
    rect(52, 293, 388, 7, teal, radius: 3)
    text("phase-N/tasks.md", 77, 319, 25, ink, bold: true, mono: true)
    text("Task: review and close", 77, 371, 24)
    text(scene == 0 ? "[/] In progress" : "[x] Done", 77, 417, 31, scene == 0 ? amber : teal, bold: true)
    text(scene == 0 ? "Evidence ready to review" : "Supported by evidence", 77, 480, 20, muted)

    let destinations: [CGFloat] = [344, 458, 572]
    for (idx, y) in destinations.enumerated() {
      let active = scene >= 2
      arrow(440, 419, 770, y, active: active)
      if scene == 2 || scene == 4 {
        let p = CGFloat(tick) / 11
        let xx = 440 + (770-440)*p, yy = 419+(y-419)*p
        rect(xx-7, yy-7, 14, 14, teal, radius: 7)
      }
      let good = scene >= 2 && !(scene <= 3 && idx == 1)
      let names = ["presentation.html", "project/README.md", "memory-bank/progress.md"]
      let subtitles = ["AUTO: status summary", "Phase overview table", "AUTO: task counts"]
      doc(774, y-49, names[idx], subtitles[idx], good ? "IN SYNC" : "STALE", good: good, active: active)
    }
    rect(497, 372, 215, 85, paper, radius: 12)
    text(scene >= 3 ? "CHECK / FIX" : "SYNC", 519, 383, 23, scene == 3 ? amber : teal, bold: true, mono: true)
    text(scene >= 3 ? "gate + review" : "derived blocks", 519, 422, 17, muted, mono: scene < 3)

    let gateColor = scene == 3 ? amber : (scene >= 4 ? teal : muted)
    rect(52, 628, 1176, 70, gateColor.withAlphaComponent(0.08), radius: 10)
    let gate = scene < 3 ? "Update the owner → Sync related blocks → Check consistency" : scene == 3 ? "GATE: ERROR — the project overview still disagrees with tasks.md" : scene == 4 ? "GATE: Recheck passes • No ERROR • Review every WARN" : "Handover: checks + limits • Azure DevOps drift checks are read-only"
    text(gate, 74, 649, 22, gateColor, bold: true)
    for i in 0..<6 {
      rect(52+CGFloat(i)*198, 725, 182, 5, i <= scene ? teal : line, radius: 2)
    }
    text(String(format: "%02d / 06", scene+1), 52, 749, 15, muted, mono: true)
    text("Companions: memory-bank + diataxis (installed separately)", 633, 746, 18, muted)
    NSGraphicsContext.restoreGraphicsState()
    let data = bitmap.representation(using: .png, properties: [:])!
    try data.write(to: URL(fileURLWithPath: output).appendingPathComponent(String(format: "%02d-%02d.png", scene, tick)))
  }
}
