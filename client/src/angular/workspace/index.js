import {mod as controllers} from './controllers';
import {mod as directives} from './directives';
import {mod as services} from './services';

import angular from 'angular';

function config($interpolateProvider, $httpProvider, $urlRouterProvider, $stateProvider, $translateProvider) {
  'ngInject';
  $stateProvider.state('tray', {
      url: '/workspace/:appId',
      templateUrl: '/static/src/angular/workspace/templates/application-tray.html',
      controller: 'ApplicationTrayCtrl'
  });

  $translateProvider.translations('en', {
      error_system_monitor: "The execution system for this app is currently unavailable. Your job submission may fail.",
      error_app_run: "Could not find appId provided",
      error_app_disabled: "The app you're trying to run is currently disabled. Please enable the app and try again",
      apps_metadata_name: "portal_apps",
      apps_metadata_list_name: "portal_apps_list"
  });
  $translateProvider.preferredLanguage('en');
}


let mod = angular.module('portal.workspace', [
  'portal.workspace.controllers',
  'portal.workspace.services',
  'portal.workspace.directives'
]).config(config)
.run(function(editableOptions) {
  editableOptions.theme = 'bs3';
});

angular.module('schemaForm').config(
['schemaFormProvider', 'schemaFormDecoratorsProvider', 'sfPathProvider',
  function(schemaFormProvider,  schemaFormDecoratorsProvider, sfPathProvider) {

    var filePicker = function(name, schema, options) {
      if (schema.type === 'string' && schema.format === 'agaveFile') {
        var f = schemaFormProvider.stdFormObj(name, schema, options);
        f.key  = options.path;
        f.type = 'agaveFilePicker';
        options.lookup[sfPathProvider.stringify(options.path)] = f;
        return f;
      }
    };

    schemaFormProvider.defaults.string.unshift(filePicker);

    //Add to the bootstrap directive
    schemaFormDecoratorsProvider.addMapping(
      'bootstrapDecorator',
      'agaveFilePicker',
      '/static/portal/scripts/angular/workspace/templates/asf-agave-file-picker.html'
    );
    schemaFormDecoratorsProvider.createDirective(
      'agaveFilePicker',
      '/static/portal/scripts/angular/workspace/templates/asf-agave-file-picker.html'
    );
  }
]);

export default mod;
