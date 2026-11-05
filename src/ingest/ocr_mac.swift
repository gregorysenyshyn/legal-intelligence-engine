import Foundation
import PDFKit
import Vision

func ocrPDF(pdfPath: String) {
    let url = URL(fileURLWithPath: pdfPath)
    guard let document = PDFDocument(url: url) else {
        print("Could not open PDF at \(pdfPath)")
        return
    }

    for pageIndex in 0..<document.pageCount {
        guard let page = document.page(at: pageIndex) else { continue }
        let pageRect = page.bounds(for: .mediaBox)
        let renderer = ImageRenderer(page: page, rect: pageRect)
        guard let cgImage = renderer.render() else { continue }

        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true

        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        try? handler.perform([request])

        guard let observations = request.results else { continue }
        let recognizedStrings = observations.compactMap { $0.topCandidates(1).first?.string }

        print("\n<!-- Page \(pageIndex + 1) -->\n## Page \(pageIndex + 1)\n")
        print(recognizedStrings.joined(separator: "\n"))
    }
}

class ImageRenderer {
    let page: PDFPage
    let rect: CGRect

    init(page: PDFPage, rect: CGRect) {
        self.page = page
        self.rect = rect
    }

    func render() -> CGImage? {
        let scale: CGFloat = 2.0
        let width = Int(rect.width * scale)
        let height = Int(rect.height * scale)
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        guard let context = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: 0,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return nil }

        context.scaleBy(x: scale, y: scale)
        context.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
        context.fill(rect)
        page.draw(with: .mediaBox, to: context)
        return context.makeImage()
    }
}

let args = CommandLine.arguments
if args.count > 1 {
    ocrPDF(pdfPath: args[1])
}
