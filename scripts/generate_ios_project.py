"""Regenerate the dependency-free Xcode project and shared scheme."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "ios"
PROJECT = ROOT / "ThriftForGood.xcodeproj"
objects = {}


def identifier(name):
    return hashlib.sha1(name.encode()).hexdigest()[:24].upper()


def add(key_name, isa, **values):
    key = identifier(key_name)
    objects[key] = {"isa": isa, **values}
    return key


def file_ref(path, file_type):
    return add("file:" + path, "PBXFileReference", lastKnownFileType=file_type, path=path, sourceTree="<group>")


def phase(target, kind, refs):
    files = [add("build:" + target + ":" + ref, "PBXBuildFile", fileRef=ref) for ref in refs]
    return add(target + ":" + kind, kind, buildActionMask=2147483647, files=files, runOnlyForDeploymentPostprocessing=0)


def configurations(name, settings):
    refs = []
    for config in ["Debug", "Release"]:
        values = dict(settings)
        if name == "project":
            values.update(SWIFT_OPTIMIZATION_LEVEL="-Onone" if config == "Debug" else "-O")
            if config == "Debug":
                values.update(ENABLE_TESTABILITY="YES", DEBUG_INFORMATION_FORMAT="dwarf",
                              SWIFT_ACTIVE_COMPILATION_CONDITIONS="DEBUG")
            else:
                values.update(DEBUG_INFORMATION_FORMAT="dwarf-with-dsym", VALIDATE_PRODUCT="YES")
        refs.append(add(name + ":" + config, "XCBuildConfiguration", buildSettings=values, name=config))
    return add(name + ":configs", "XCConfigurationList", buildConfigurations=refs,
               defaultConfigurationIsVisible=0, defaultConfigurationName="Release")


sources = [file_ref(str(path.relative_to(ROOT)).replace("\\", "/"), "sourcecode.swift")
           for path in sorted((ROOT / "Sources").rglob("*.swift"))]
unit = [file_ref("Tests/ServerPolicyTests.swift", "sourcecode.swift")]
ui = [file_ref("UITests/ConnectionScreenTests.swift", "sourcecode.swift")]
resources = [
    file_ref("Sources/Assets.xcassets", "folder.assetcatalog"),
    file_ref("Sources/LaunchScreen.storyboard", "file.storyboard"),
    file_ref("Sources/PrivacyInfo.xcprivacy", "text.xml"),
]
info = file_ref("Sources/Info.plist", "text.plist.xml")
products = []
targets = []
app_id = identifier("target:ThriftForGood")
for name, product_type, files, suffix in [
    ("ThriftForGood", "com.apple.product-type.application", sources, "app"),
    ("ThriftForGoodTests", "com.apple.product-type.bundle.unit-test", unit, "xctest"),
    ("ThriftForGoodUITests", "com.apple.product-type.bundle.ui-testing", ui, "xctest"),
]:
    product = add(name + ":product", "PBXFileReference", explicitFileType="wrapper.application" if suffix == "app" else "wrapper.cfbundle",
                  includeInIndex=0, path=name + "." + suffix, sourceTree="BUILT_PRODUCTS_DIR")
    products.append(product)
    settings = dict(PRODUCT_NAME="$(TARGET_NAME)", PRODUCT_BUNDLE_IDENTIFIER="org.givingflow.mobile",
                    CODE_SIGN_STYLE="Automatic", DEVELOPMENT_TEAM="", TARGETED_DEVICE_FAMILY="1,2")
    dependencies = []
    if name == "ThriftForGood":
        settings.update(INFOPLIST_FILE="Sources/Info.plist", GENERATE_INFOPLIST_FILE="NO",
                        ASSETCATALOG_COMPILER_APPICON_NAME="AppIcon", MARKETING_VERSION="0.4.0",
                        CURRENT_PROJECT_VERSION="1", SUPPORTED_PLATFORMS="iphoneos iphonesimulator",
                        SUPPORTS_MACCATALYST="NO", LD_RUNPATH_SEARCH_PATHS="$(inherited) @executable_path/Frameworks")
    else:
        proxy = add(name + ":proxy", "PBXContainerItemProxy", containerPortal=identifier("project"),
                    proxyType=1, remoteGlobalIDString=app_id, remoteInfo="ThriftForGood")
        dependencies = [add(name + ":dependency", "PBXTargetDependency", target=app_id, targetProxy=proxy)]
        settings.update(GENERATE_INFOPLIST_FILE="YES", PRODUCT_BUNDLE_IDENTIFIER="org.givingflow.mobile." + suffix + name,
                        LD_RUNPATH_SEARCH_PATHS="$(inherited) @executable_path/Frameworks @loader_path/Frameworks")
        if name.endswith("UITests"):
            settings.update(TEST_TARGET_NAME="ThriftForGood")
        else:
            settings.update(TEST_HOST="$(BUILT_PRODUCTS_DIR)/ThriftForGood.app/ThriftForGood", BUNDLE_LOADER="$(TEST_HOST)")
    targets.append(add("target:" + name, "PBXNativeTarget", name=name, productName=name,
                       productType=product_type, productReference=product,
                       buildConfigurationList=configurations(name, settings),
                       buildPhases=[phase(name, "PBXSourcesBuildPhase", files),
                                    phase(name, "PBXFrameworksBuildPhase", []),
                                    phase(name, "PBXResourcesBuildPhase", resources if suffix == "app" else [])],
                       buildRules=[], dependencies=dependencies))

product_group = add("products", "PBXGroup", children=products, name="Products", sourceTree="<group>")
source_group = add("sources", "PBXGroup", children=sources + resources + [info], name="Sources", sourceTree="<group>")
test_group = add("tests", "PBXGroup", children=unit + ui, name="Tests", sourceTree="<group>")
main_group = add("main", "PBXGroup", children=[source_group, test_group, product_group], sourceTree="<group>")
project_config = configurations("project", dict(
    IPHONEOS_DEPLOYMENT_TARGET="16.0", SDKROOT="iphoneos", SWIFT_VERSION="5.0",
    SWIFT_STRICT_CONCURRENCY="minimal", CLANG_ENABLE_MODULES="YES", CLANG_ENABLE_OBJC_ARC="YES",
    ENABLE_USER_SCRIPT_SANDBOXING="YES", GCC_C_LANGUAGE_STANDARD="gnu17", ONLY_ACTIVE_ARCH="YES"
))
target_attributes = {target: {"CreatedOnToolsVersion": "16.0"} for target in targets}
for target in targets[1:]:
    target_attributes[target]["TestTargetID"] = app_id
root = add("project", "PBXProject", attributes={"BuildIndependentTargetsInParallel": "YES",
           "LastUpgradeCheck": "1600", "TargetAttributes": target_attributes},
           buildConfigurationList=project_config, compatibilityVersion="Xcode 14.0",
           developmentRegion="en", hasScannedForEncodings=0, knownRegions=["en", "Base"],
           mainGroup=main_group, productRefGroup=product_group, projectDirPath="", projectRoot="", targets=targets)


def plist(value, level=0):
    indent = "\t" * level
    if isinstance(value, dict):
        body = "\n".join("\t" * (level + 1) + json.dumps(key) + " = " + plist(item, level + 1) + ";"
                         for key, item in value.items())
        return "{\n" + body + "\n" + indent + "}"
    if isinstance(value, list):
        return "(\n" + "".join("\t" * (level + 1) + plist(item, level + 1) + ",\n" for item in value) + indent + ")"
    return str(value) if isinstance(value, int) else json.dumps(value)


PROJECT.mkdir(parents=True, exist_ok=True)
(PROJECT / "project.pbxproj").write_text("// !$*UTF8*$!\n" + plist(dict(archiveVersion=1, classes={}, objectVersion=56,
                                                               objects=objects, rootObject=root)) + "\n", encoding="utf-8")
scheme = ET.Element("Scheme", LastUpgradeVersion="1600", version="1.7")
build = ET.SubElement(scheme, "BuildAction", parallelizeBuildables="YES", buildImplicitDependencies="YES")
entries = ET.SubElement(build, "BuildActionEntries")


def buildable(parent, name, extension):
    ET.SubElement(parent, "BuildableReference", BuildableIdentifier="primary", BlueprintIdentifier=identifier("target:" + name),
                  BuildableName=name + "." + extension, BlueprintName=name, ReferencedContainer="container:ThriftForGood.xcodeproj")


for name, extension in [("ThriftForGood", "app"), ("ThriftForGoodTests", "xctest"), ("ThriftForGoodUITests", "xctest")]:
    app = extension == "app"
    entry = ET.SubElement(entries, "BuildActionEntry", buildForTesting="YES", buildForRunning="YES" if app else "NO",
                          buildForProfiling="YES" if app else "NO", buildForArchiving="YES" if app else "NO",
                          buildForAnalyzing="YES" if app else "NO")
    buildable(entry, name, extension)
test_action = ET.SubElement(scheme, "TestAction", buildConfiguration="Debug",
                            selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB",
                            selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB", shouldUseLaunchSchemeArgsEnv="YES")
buildable(ET.SubElement(test_action, "MacroExpansion"), "ThriftForGood", "app")
testables = ET.SubElement(test_action, "Testables")
for name in ["ThriftForGoodTests", "ThriftForGoodUITests"]:
    buildable(ET.SubElement(testables, "TestableReference", skipped="NO"), name, "xctest")
for action, config in [("LaunchAction", "Debug"), ("ProfileAction", "Release")]:
    node = ET.SubElement(scheme, action, buildConfiguration=config, shouldUseLaunchSchemeArgsEnv="YES")
    buildable(ET.SubElement(node, "BuildableProductRunnable", runnableDebuggingMode="0"), "ThriftForGood", "app")
ET.SubElement(scheme, "AnalyzeAction", buildConfiguration="Debug")
ET.SubElement(scheme, "ArchiveAction", buildConfiguration="Release", revealArchiveInOrganizer="YES")
ET.indent(scheme, space="  ")
scheme_dir = PROJECT / "xcshareddata" / "xcschemes"
scheme_dir.mkdir(parents=True, exist_ok=True)
ET.ElementTree(scheme).write(scheme_dir / "ThriftForGood.xcscheme", encoding="UTF-8", xml_declaration=True)
print("Generated", PROJECT)
