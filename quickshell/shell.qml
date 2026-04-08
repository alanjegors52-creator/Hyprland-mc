import Quickshell
import Quickshell.Wayland
import Quickshell.Io
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls 2.1
import "./"

ShellRoot {

    // ══════════════════════════════════════════
    //  CLOCK WIDGET
    // ══════════════════════════════════════════
    PanelWindow {
        // Only anchor to top so we can control width/position freely
        anchors.top: true
        anchors.left: true

        // Fixed size — wide enough for WEDNESDAY at pixelSize 90
        implicitWidth: 700
        implicitHeight: 250

        // Push it down from the top edge
        margins.top: 0
        margins.left: 0

        WlrLayershell.layer: WlrLayer.Background
        WlrLayershell.namespace: "clock-widget"
        WlrLayershell.exclusiveZone: -1
        color: "transparent"

        FontLoader {
            id: font_anurati
            source: Qt.resolvedUrl("./Minecraft.ttf")
        }
        FontLoader {
            id: font_poppins
            source: Qt.resolvedUrl("./Minecraft.ttf")
        }

        SystemClock {
            id: clock
            precision: SystemClock.Seconds
        }

        Column {
            anchors.centerIn: parent
            spacing: 4

            Item {
                implicitWidth: clock_day.implicitWidth
                implicitHeight: clock_day.implicitHeight
                anchors.horizontalCenter: parent.horizontalCenter
                Text { x: 2; y: 2; text: clock_day.text; font: clock_day.font; color: "#55000000" }
                Text {
                    id: clock_day
                    text: Qt.formatDate(clock.date, "dddd").toUpperCase()
                    font.family: font_anurati.name
                    font.pixelSize: 90
                    color: "#ffffff"
                    font.letterSpacing: 10
                }
            }

            Item {
                implicitWidth: clock_date.implicitWidth
                implicitHeight: clock_date.implicitHeight
                anchors.horizontalCenter: parent.horizontalCenter
                Text { x: 1; y: 1; text: clock_date.text; font: clock_date.font; color: "#55000000" }
                Text {
                    id: clock_date
                    text: Qt.formatDate(clock.date, "dd MMM yyyy").toUpperCase()
                    font.family: font_poppins.name
                    font.pixelSize: 20
                    color: "#ffffff"
                }
            }

            Item {
                implicitWidth: clock_time.implicitWidth
                implicitHeight: clock_time.implicitHeight
                anchors.horizontalCenter: parent.horizontalCenter
                Text { x: 1; y: 1; text: clock_time.text; font: clock_time.font; color: "#55000000" }
                Text {
                    id: clock_time
                    text: "- " + Qt.formatTime(clock.date, "hh:mm:ss") + " -"
                    font.family: font_poppins.name
                    font.pixelSize: 17
                    color: "#ffffff"
                }
            }
        }
    }

    // ══════════════════════════════════════════
    //  HOTBAR
    // ══════════════════════════════════════════
    PanelWindow {
        id: hotbarWindow
        anchors.bottom: true
        anchors.left: true
        anchors.right: true

        implicitHeight: 61
        color: "transparent"

        WlrLayershell.layer: WlrLayer.Top
        WlrLayershell.exclusiveZone: 61
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

        Image {
            anchors.centerIn: parent
            source: Qt.resolvedUrl("./hotbar.png")
            fillMode: Image.Pad
            smooth: false
        }

        Row {
            anchors.centerIn: parent
            spacing: 0

            Repeater {
                model: hotbarModel

                Item {
                    width: 60
                    height: 61

                    Image {
                        anchors.centerIn: parent
                        width: 36
                        height: 36
                        source: modelData.icon
                        smooth: true
                        visible: modelData.icon !== ""
                    }

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 6
                        color: "#ffffff"
                        opacity: hoverHandler.hovered ? 0.15 : 0
                        Behavior on opacity { NumberAnimation { duration: 80 } }
                    }

                    HoverHandler { id: hoverHandler }

                    TapHandler {
                        onTapped: {
                            if (modelData.cmd !== "") {
                                launcher.command = ["sh", "-c", modelData.cmd + " &"]
                                launcher.running = true
                            }
                        }
                    }

                    Rectangle {
                        visible: hoverHandler.hovered && modelData.name !== ""
                        anchors.bottom: parent.top
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottomMargin: 4
                        color: "#100010"
                        border.color: "#5000a0"
                        border.width: 2
                        width: tipText.width + 12
                        height: tipText.height + 8
                        Text {
                            id: tipText
                            anchors.centerIn: parent
                            text: modelData.name
                            color: "#ffffff"
                            font.pixelSize: 13
                            font.family: "monospace"
                        }
                    }
                }
            }
        }

        Process {
            id: launcher
            running: false
        }
    }

    // ── Slot data ─────────────────────────────
    property var hotbarModel: [
        { name: "Zen",      cmd: "zen-browser",     icon: "image://icon/zen-browser" },
        { name: "Terminal", cmd: "kitty",            icon: "image://icon/kitty" },
        { name: "Minecraft",    cmd: "'prismlauncher' '--launch' 'Minecraft'",    icon: "/home/alan/.local/share/PrismLauncher/icons/mine.png" },
        { name: "",         cmd: "",                 icon: "" },
        { name: "",         cmd: "",                 icon: "" },
        { name: "",         cmd: "",                 icon: "" },
        { name: "",         cmd: "",                 icon: "" },
        { name: "",         cmd: "",                 icon: "" },
        { name: "",         cmd: "",                 icon: "" }
    ]
}
