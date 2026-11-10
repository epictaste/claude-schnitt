// Augenhöhe per macOS Vision messen, damit Augen und Gesicht im Video immer auf gleicher Höhe bleiben.
// Kompilieren: swiftc -O augen.swift -o augen   (macht setup.py)
// Aufruf: augen <bild1.png> [bild2.png …]
// Ausgabe je Zeile: datei augenY augenX (Pixel, Ursprung oben links, Mitte zwischen beiden Pupillen).
// Kein Gesicht: "datei KEIN_GESICHT", Bild nicht lesbar: "datei FEHLER".
import Foundation
import Vision
import AppKit

for pfad in CommandLine.arguments.dropFirst() {
    guard let bild = NSImage(contentsOfFile: pfad), let cg = bild.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("\(pfad) FEHLER"); continue }
    let w = Double(cg.width), h = Double(cg.height)
    let req = VNDetectFaceLandmarksRequest()
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    guard let f = (req.results ?? []).max(by: { $0.boundingBox.width < $1.boundingBox.width }), let lm = f.landmarks,
          let l = lm.leftPupil?.normalizedPoints.first, let r = lm.rightPupil?.normalizedPoints.first else { print("\(pfad) KEIN_GESICHT"); continue }
    let bb = f.boundingBox
    let px = { (p: CGPoint) -> (Double, Double) in (Double(bb.minX + p.x * bb.width) * w, (1 - Double(bb.minY + p.y * bb.height)) * h) }
    let (lx, ly) = px(l), (rx, ry) = px(r)
    print(String(format: "%@ %.1f %.1f", pfad, (ly + ry) / 2, (lx + rx) / 2))
}
