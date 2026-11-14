import XCTest

final class ConnectionScreenTests: XCTestCase {
    func testServerScreenAndInvalidAddress() {
        let app = XCUIApplication()
        app.launchArguments = ["--uitesting"]
        app.launch()
        let address = app.textFields["serverAddress"]
        XCTAssertTrue(address.waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["connectServer"].exists)
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "PC connection screen"
        screenshot.lifetime = .keepAlways
        add(screenshot)
        address.tap()
        if let value = address.value as? String, !value.isEmpty {
            address.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: value.count))
        }
        address.typeText("http://example.org:8000")
        app.buttons["connectServer"].tap()
        XCTAssertTrue(app.staticTexts["connectionStatus"].label.contains("trusted HTTPS"))
    }
}
