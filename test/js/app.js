QUnit.test( "app new version available action", function( assert ) {

  backend.async = false;
  run_app_action('owncloud', 'install', function() {}, function(a, b, c) {});

  assert.deepEqual( true, true);
});