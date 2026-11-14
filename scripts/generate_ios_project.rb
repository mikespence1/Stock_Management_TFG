# Regenerate with: gem install xcodeproj -v 1.28.1 && ruby scripts/generate_ios_project.rb
require 'xcodeproj'

root = File.expand_path('../ios', __dir__)
project = Xcodeproj::Project.new(File.join(root, 'ThriftForGood.xcodeproj'), false, 56)
app = project.new_target(:application, 'ThriftForGood', :ios, '16.0')
unit = project.new_target(:unit_test_bundle, 'ThriftForGoodTests', :ios, '16.0')
ui = project.new_target(:ui_test_bundle, 'ThriftForGoodUITests', :ios, '16.0')
source_group = project.main_group.new_group('Sources')
test_group = project.main_group.new_group('Tests')

Dir.glob(File.join(root, 'Sources/**/*.swift')).sort.each do |path|
  ref = source_group.new_file(path.delete_prefix(root + '/'))
  app.source_build_phase.add_file_reference(ref)
end
%w[Sources/Assets.xcassets Sources/LaunchScreen.storyboard Sources/PrivacyInfo.xcprivacy].each do |path|
  app.resources_build_phase.add_file_reference(source_group.new_file(path))
end
source_group.new_file('Sources/Info.plist')
unit.source_build_phase.add_file_reference(test_group.new_file('Tests/ServerPolicyTests.swift'))
ui.source_build_phase.add_file_reference(test_group.new_file('UITests/ConnectionScreenTests.swift'))
unit.add_dependency(app)
ui.add_dependency(app)

project.build_configurations.each do |config|
  config.build_settings.merge!(
    'SWIFT_VERSION' => '5.0', 'SWIFT_STRICT_CONCURRENCY' => 'minimal',
    'IPHONEOS_DEPLOYMENT_TARGET' => '16.0', 'ENABLE_USER_SCRIPT_SANDBOXING' => 'YES'
  )
end
project.targets.each do |target|
  target.build_configurations.each do |config|
    config.build_settings.merge!(
      'PRODUCT_NAME' => '$(TARGET_NAME)', 'CODE_SIGN_STYLE' => 'Automatic',
      'DEVELOPMENT_TEAM' => '', 'SWIFT_VERSION' => '5.0', 'TARGETED_DEVICE_FAMILY' => '1,2'
    )
    config.build_settings['ENABLE_TESTABILITY'] = 'YES' if config.name == 'Debug'
  end
end
app.build_configurations.each do |config|
  config.build_settings.merge!(
    'PRODUCT_BUNDLE_IDENTIFIER' => 'org.givingflow.mobile', 'INFOPLIST_FILE' => 'Sources/Info.plist',
    'GENERATE_INFOPLIST_FILE' => 'NO', 'ASSETCATALOG_COMPILER_APPICON_NAME' => 'AppIcon',
    'MARKETING_VERSION' => '0.4.0', 'CURRENT_PROJECT_VERSION' => '1', 'SUPPORTS_MACCATALYST' => 'NO',
    'LD_RUNPATH_SEARCH_PATHS' => '$(inherited) @executable_path/Frameworks'
  )
end
unit.build_configurations.each do |config|
  config.build_settings.merge!(
    'PRODUCT_BUNDLE_IDENTIFIER' => 'org.givingflow.mobile.tests', 'GENERATE_INFOPLIST_FILE' => 'YES',
    'TEST_HOST' => '$(BUILT_PRODUCTS_DIR)/ThriftForGood.app/ThriftForGood', 'BUNDLE_LOADER' => '$(TEST_HOST)'
  )
end
ui.build_configurations.each do |config|
  config.build_settings.merge!(
    'PRODUCT_BUNDLE_IDENTIFIER' => 'org.givingflow.mobile.uitests', 'GENERATE_INFOPLIST_FILE' => 'YES',
    'TEST_TARGET_NAME' => 'ThriftForGood'
  )
end
project.root_object.attributes['LastUpgradeCheck'] = '1600'
project.sort
project.predictabilize_uuids
project.save
scheme = Xcodeproj::XCScheme.new
scheme.configure_with_targets(app, unit, launch_target: true)
scheme.add_build_target(ui, false)
scheme.add_test_target(ui)
scheme.save_as(project.path, 'ThriftForGood', true)
puts "Generated #{project.path}"
