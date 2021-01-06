  def check_allowed_connectors(self, resource_id):
    """
    Checks if the connectors used in the workflow are valid or not.

    Args:
      resource_id (str): Resource ID of the logic app account.

    Returns:
      dict: Returns status of Enforcement Test and list of
      connectors ID to be deleted.

    """
    result = {'status': True, 'inv_connectors': []}
    try:
      project_id = core.Helper.get_resource_group_name_from_resource_id(
        resource_id).rsplit("-", 2)[0].upper()
      project_data = project_module.get_project_info(project_id)
      subscription = project_data.subscription_id
      la_details = self.get_logic_app_details(resource_id)
      allowed_connectors = self.get_allowed_connectors(resource_id)
      if '$connections' not in la_details['properties']['parameters']:
        return result
      else:
        values = la_details['properties']['parameters']['$connections']['value']
        for connector in values:
          connector_url = (core.CONST_ARM_MANAGEMENT_URI + values[connector][
            'connectionId'])
          connector_type = values[connector]['id'].split("/")[-1].lower()
          if (connector_type not in allowed_connectors):
            result['inv_connectors'].append(values[connector]['connectionId'])
            result['status'] = False
          elif (connector_type in allowed_connectors):
            try:
              connector_details = self.azure_restful_client.get(
                connector_url, self.logicapps_api_version)
            except:
              continue
            if connector_type == 'documentdb':
              docdb_exists = False
              docdb_name = connector_details['properties'][
                'nonSecretParameterValues']['databaseAccount'].lower()
              for application in project_data.applications:
                for environment in application.environments:
                  rg_name = environment.resource_group
                  docdb_res_url = (core.CONST_ARM_MANAGEMENT_URL + subscription
                                   + '/resourceGroups/' + rg_name +
                                   '/providers/Microsoft.DocumentDB/'
                                   'databaseAccounts')
                  docdb_instances = self.azure_restful_client.get(docdb_res_url,
                                                                  '2020-04-01')
                  for docdb_instance in docdb_instances['value']:
                    if docdb_name == docdb_instance['name'].lower():
                      docdb_exists = True
                      break
              if not docdb_exists:
                result['inv_connectors'].append(values[connector][
                                                  'connectionId'])
                result['status'] = False
            elif connector_type in ['azureblob', 'azuretables', 'azurequeues']:
              storage_account_exists = False
              if connector_type == 'azureblob':
                storage_account_name = connector_details['properties'][
                  'nonSecretParameterValues']['accountName'].lower()
              else:
                storage_account_name = connector_details['properties'][
                  'nonSecretParameterValues']['storageaccount'].lower()
              for application in project_data.applications:
                for environment in application.environments:
                  rg_name = environment.resource_group
                  storage_accounts_url = (core.CONST_ARM_MANAGEMENT_URL +
                                          subscription + '/resourceGroups/' +
                                          rg_name + '/providers/' +
                                          'Microsoft.Storage/storageAccounts')
                  storage_account_instances = self.azure_restful_client.get(
                    storage_accounts_url, '2019-06-01')
                  for storage_account_instance in storage_account_instances[
                    'value']:
                    if storage_account_name == storage_account_instance[
                      'name'].lower():
                      storage_account_exists = True
                      break
              if not storage_account_exists:
                result['inv_connectors'].append(values[connector][
                                                  'connectionId'])
                result['status'] = False
            elif connector_type in ['sql', 'sqldw']:
              sql_server_exists = False
              if connector_type == 'sqldw':
                sql_server_name = connector_details['properties'][
                  'nonSecretParameterValues']['server'].lower()
              elif connector_type == 'sql':
                if connector_details['properties']['parameterValueSet'][
                  'name'].lower() == 'sqlauthentication':
                  if connector_details['properties']['parameterValueSet'][
                    'values']['server']['value'].lower().endswith('microsoft.com'):
                    continue
                  else:
                    sql_server_name = connector_details['properties'][
                      'parameterValueSet']['values']['server']['value'].lower()
              for application in project_data.applications:
                for environment in application.environments:
                  rg_name = environment.resource_group
                  sql_servers_url = (core.CONST_ARM_MANAGEMENT_URL +
                                     subscription + '/resourceGroups/' +
                                     rg_name + '/providers/' +
                                     'Microsoft.Sql/servers')
                  sql_server_instances = self.azure_restful_client.get(
                    sql_servers_url, '2019-06-01-preview')
                  for sql_server_instance in sql_server_instances['value']:
                    if sql_server_name == sql_server_instance['properties'][
                      'fullyQualifiedDomainName'].lower():
                      sql_server_exists = True
                      break
              if not sql_server_exists:
                result['inv_connectors'].append(values[connector][
                                                  'connectionId'])
                result['status'] = False
            elif connector_type in ['office365', 'excelonlinebusiness',
                                    'sharepointonline']:
              username = connector_details['properties']['authenticatedUser'][
                'name'].lower()
              if not username.endswith('microsoft.com'):
                result['inv_connectors'].append(values[connector][
                                                  'connectionId'])
                result['status'] = False
            elif connector_type == 'applicationinsights':
              app_insight_exists = False
              app_id = connector_details['properties'][
                'nonSecretParameterValues']['username'].lower()
              for application in project_data.applications:
                for environment in application.environments:
                  rg_name = environment.resource_group
                  ai_res_url = (core.CONST_ARM_MANAGEMENT_URL + subscription
                                + '/resourceGroups/' + rg_name +
                                '/providers/Microsoft.Insights/components')
                  ai_instances = self.azure_restful_client.get(ai_res_url,
                                                               '2015-05-01')
                  for ai_instance in ai_instances['value']:
                    if app_id == ai_instance['properties']['AppId'].lower():
                      app_insight_exists = True
                      break
              if not app_insight_exists:
                result['inv_connectors'].append(values[connector][
                                                  'connectionId'])
                result['status'] = False
            elif connector_type in ['azuredatafactory', 'azuredatalake']:
              if 'name' in connector_details['properties']['authenticatedUser']:
                username = connector_details['properties']['authenticatedUser'][
                  'name'].lower()
                tenant_id = connector_details['properties'][
                  'nonSecretParameterValues']['token:TenantId'].lower()
                if not (username.endswith('microsoft.com') and tenant_id ==
                        core.CONST_AUTH_TENANT_ID):
                  result['inv_connectors'].append(values[connector][
                                                  'connectionId'])
                  result['status'] = False
              else:
                tenant_id = connector_details['properties'][
                  'nonSecretParameterValues']['token:TenantId'].lower()
                if tenant_id != core.CONST_AUTH_TENANT_ID:
                  result['inv_connectors'].append(connector_url)
                  result['status'] = False
    except Exception as E:
      raise XError(str(E))
    return result

  def get_allowed_connectors(self, resource_id):
    """
    Fetches the global allowed connectors list and project specific list,
    compares them, and combines them

    Args:
      resource_id (str): Resource ID of the logic app account.

    Returns:
      Returns combined allowed connectors list.

    """
    project_connector_list = []
    global_connector_list = []
    result = []
    try:
      resource_group = core.Helper.get_resource_group_name_from_resource_id(
        resource_id)
      project_id = resource_group.rsplit("-", 2)[0].upper()
      project_data = project_module.get_project_info(project_id)
      project_connector_list = project_data.logic_apps_allowed_connectors
      table_service = core.Helper.get_table_service()
      entities = table_service.query_entities(core.CONST_TABLE_LOOKUP)
      for entity in entities:
        if (entity.RowKey == 'allowed_connectors' and entity.PartitionKey ==
            'Lookup'):
          global_connector_list = entity.values.split(",")
          break
      result = (global_connector_list + list(set(project_connector_list) -
                                             set(global_connector_list)))
      if not result:
        msg = ['REDACTED']
        raise XError(msg)
    except Exception as E:
      raise XError(str(E))
    return result

  def delete_connectors(self, resource_id, inv_connectors):
    """
    Delete invalid connectors in the logic app workflow.

    Args:
      resource_id (str): Resource ID of the logic app account.
      inv_connectors (list): List of connectors ID to be deleted.

    Returns:
      bool: Returns True if the operation is successful.

    """
    try:
      la_details = self.get_logic_app_details(resource_id)
      connectors = copy.deepcopy(la_details['properties']['parameters'][
                                   '$connections']['value'])
      for inv_connector in inv_connectors:
        connector_url = core.CONST_ARM_MANAGEMENT_URI + inv_connector
        self.azure_restful_client.delete(connector_url,
                                         self.logicapps_api_version)
        for connector in connectors:
          if connectors[connector]['connectionId'] == inv_connector:
            del la_details['properties']['parameters']['$connections']['value'][
              connector]
      self.update_logicapp(la_details, resource_id)
    except Exception as E:
      raise XError(str(E))
    return True