import React from 'react';
import { ActivityIndicator, View } from 'react-native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from '../auth/AuthContext';
import { t } from '../i18n';
import { theme } from '../theme';
import LoginScreen from '../screens/LoginScreen';
import HomeScreen from '../screens/HomeScreen';
import UserScreen from '../screens/UserScreen';
import UserFormScreen from '../screens/UserFormScreen';
import UserMfaScreen from '../screens/UserMfaScreen';
import UserMfaFormScreen from '../screens/UserMfaFormScreen';
import PayrollPeriodScreen from '../screens/PayrollPeriodScreen';
import PayrollPeriodFormScreen from '../screens/PayrollPeriodFormScreen';
import PayrollDetailScreen from '../screens/PayrollDetailScreen';
import PayrollDetailFormScreen from '../screens/PayrollDetailFormScreen';
import PayrollConceptScreen from '../screens/PayrollConceptScreen';
import PayrollConceptFormScreen from '../screens/PayrollConceptFormScreen';
import PayrollMovementScreen from '../screens/PayrollMovementScreen';
import PayrollMovementFormScreen from '../screens/PayrollMovementFormScreen';
import CustomerSupplierScreen from '../screens/CustomerSupplierScreen';
import CustomerSupplierFormScreen from '../screens/CustomerSupplierFormScreen';
import ProyectScreen from '../screens/ProyectScreen';
import ProyectFormScreen from '../screens/ProyectFormScreen';
import BankScreen from '../screens/BankScreen';
import BankFormScreen from '../screens/BankFormScreen';
import BankAccountScreen from '../screens/BankAccountScreen';
import BankAccountFormScreen from '../screens/BankAccountFormScreen';
import InvoiceScreen from '../screens/InvoiceScreen';
import InvoiceFormScreen from '../screens/InvoiceFormScreen';
import InvoiceMaterialServiceScreen from '../screens/InvoiceMaterialServiceScreen';
import InvoiceMaterialServiceFormScreen from '../screens/InvoiceMaterialServiceFormScreen';
import ProductFamilyScreen from '../screens/ProductFamilyScreen';
import ProductFamilyFormScreen from '../screens/ProductFamilyFormScreen';
import IncidentTypeScreen from '../screens/IncidentTypeScreen';
import IncidentTypeFormScreen from '../screens/IncidentTypeFormScreen';
import IncidentScreen from '../screens/IncidentScreen';
import IncidentFormScreen from '../screens/IncidentFormScreen';
import IncidentDetailScreen from '../screens/IncidentDetailScreen';
import IncidentDetailFormScreen from '../screens/IncidentDetailFormScreen';
import BrandScreen from '../screens/BrandScreen';
import BrandFormScreen from '../screens/BrandFormScreen';
import UnitScreen from '../screens/UnitScreen';
import UnitFormScreen from '../screens/UnitFormScreen';
import MaterialScreen from '../screens/MaterialScreen';
import MaterialFormScreen from '../screens/MaterialFormScreen';
import MaterialComponentScreen from '../screens/MaterialComponentScreen';
import MaterialComponentFormScreen from '../screens/MaterialComponentFormScreen';
import MovementScreen from '../screens/MovementScreen';
import MovementFormScreen from '../screens/MovementFormScreen';
import LocationTypeScreen from '../screens/LocationTypeScreen';
import LocationTypeFormScreen from '../screens/LocationTypeFormScreen';
import LocationScreen from '../screens/LocationScreen';
import LocationFormScreen from '../screens/LocationFormScreen';
import ProductScreen from '../screens/ProductScreen';
import ProductFormScreen from '../screens/ProductFormScreen';
import NmIncidentProductScreen from '../screens/NmIncidentProductScreen';
import NmIncidentProductFormScreen from '../screens/NmIncidentProductFormScreen';
import TaskScreen from '../screens/TaskScreen';
import TaskFormScreen from '../screens/TaskFormScreen';
import TaskNoteScreen from '../screens/TaskNoteScreen';
import TaskNoteFormScreen from '../screens/TaskNoteFormScreen';
import TicketScreen from '../screens/TicketScreen';
import TicketFormScreen from '../screens/TicketFormScreen';
import FiscalAccountScreen from '../screens/FiscalAccountScreen';
import FiscalAccountFormScreen from '../screens/FiscalAccountFormScreen';
import FiscalStampScreen from '../screens/FiscalStampScreen';
import FiscalStampFormScreen from '../screens/FiscalStampFormScreen';
import FiscalRecordScreen from '../screens/FiscalRecordScreen';
import FiscalRecordFormScreen from '../screens/FiscalRecordFormScreen';
import ServiceScreen from '../screens/ServiceScreen';
import ServiceFormScreen from '../screens/ServiceFormScreen';
import StatusScreen from '../screens/StatusScreen';
import StatusFormScreen from '../screens/StatusFormScreen';
import ThemeScreen from '../screens/ThemeScreen';
import ThemeFormScreen from '../screens/ThemeFormScreen';
import DepartmentScreen from '../screens/DepartmentScreen';
import DepartmentFormScreen from '../screens/DepartmentFormScreen';
import SubdepartmentScreen from '../screens/SubdepartmentScreen';
import SubdepartmentFormScreen from '../screens/SubdepartmentFormScreen';
import LevelScreen from '../screens/LevelScreen';
import LevelFormScreen from '../screens/LevelFormScreen';
import FieldScreen from '../screens/FieldScreen';
import FieldFormScreen from '../screens/FieldFormScreen';
import PermissionScreen from '../screens/PermissionScreen';
import PermissionFormScreen from '../screens/PermissionFormScreen';
import NmFieldPermissionScreen from '../screens/NmFieldPermissionScreen';
import NmFieldPermissionFormScreen from '../screens/NmFieldPermissionFormScreen';
import EventLogScreen from '../screens/EventLogScreen';
import EventLogFormScreen from '../screens/EventLogFormScreen';
import TaskTypeScreen from '../screens/TaskTypeScreen';
import TaskTypeFormScreen from '../screens/TaskTypeFormScreen';
import TemplateScreen from '../screens/TemplateScreen';
import TemplateFormScreen from '../screens/TemplateFormScreen';
import NmTemplateTaskScreen from '../screens/NmTemplateTaskScreen';
import NmTemplateTaskFormScreen from '../screens/NmTemplateTaskFormScreen';
import SurveyQuestionScreen from '../screens/SurveyQuestionScreen';
import SurveyQuestionFormScreen from '../screens/SurveyQuestionFormScreen';
import SurveyMultipleAnswerScreen from '../screens/SurveyMultipleAnswerScreen';
import SurveyMultipleAnswerFormScreen from '../screens/SurveyMultipleAnswerFormScreen';
import NmSurveyUserScreen from '../screens/NmSurveyUserScreen';
import NmSurveyUserFormScreen from '../screens/NmSurveyUserFormScreen';
import EntityPermissionScreen from '../screens/EntityPermissionScreen';
import EntityPermissionFormScreen from '../screens/EntityPermissionFormScreen';
import InventoryStatusScreen from '../screens/InventoryStatusScreen';
import InventoryStatusFormScreen from '../screens/InventoryStatusFormScreen';
import ProductSaleConfigScreen from '../screens/ProductSaleConfigScreen';
import ProductSaleConfigFormScreen from '../screens/ProductSaleConfigFormScreen';
import PublicApiKeyScreen from '../screens/PublicApiKeyScreen';
import PublicApiKeyFormScreen from '../screens/PublicApiKeyFormScreen';

const Stack = createNativeStackNavigator();

export default function AppNavigator() {
  const { token, loading } = useAuth();
  if (loading) return <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}><ActivityIndicator /></View>;

  return (
    <Stack.Navigator screenOptions={{
      headerStyle: { backgroundColor: theme.colors.ink },
      headerTintColor: '#fff',
      contentStyle: { backgroundColor: theme.colors.bg },
    }}>
      {!token ? (
        <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
      ) : (
        <>
          <Stack.Screen name="Home" component={HomeScreen} options={{ title: t('common.dashboard') }} />
        <Stack.Screen name="User" component={UserScreen} options={{ title: t('menu.user') }} />
        <Stack.Screen name="UserForm" component={UserFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="UserMfa" component={UserMfaScreen} options={{ title: t('menu.user_mfa') }} />
        <Stack.Screen name="UserMfaForm" component={UserMfaFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="PayrollPeriod" component={PayrollPeriodScreen} options={{ title: t('menu.payroll_period') }} />
        <Stack.Screen name="PayrollPeriodForm" component={PayrollPeriodFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="PayrollDetail" component={PayrollDetailScreen} options={{ title: t('menu.payroll_detail') }} />
        <Stack.Screen name="PayrollDetailForm" component={PayrollDetailFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="PayrollConcept" component={PayrollConceptScreen} options={{ title: t('menu.payroll_concept') }} />
        <Stack.Screen name="PayrollConceptForm" component={PayrollConceptFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="PayrollMovement" component={PayrollMovementScreen} options={{ title: t('menu.payroll_movement') }} />
        <Stack.Screen name="PayrollMovementForm" component={PayrollMovementFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="CustomerSupplier" component={CustomerSupplierScreen} options={{ title: t('menu.customer_supplier') }} />
        <Stack.Screen name="CustomerSupplierForm" component={CustomerSupplierFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Proyect" component={ProyectScreen} options={{ title: t('menu.proyect') }} />
        <Stack.Screen name="ProyectForm" component={ProyectFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Bank" component={BankScreen} options={{ title: t('menu.bank') }} />
        <Stack.Screen name="BankForm" component={BankFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="BankAccount" component={BankAccountScreen} options={{ title: t('menu.bank_account') }} />
        <Stack.Screen name="BankAccountForm" component={BankAccountFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Invoice" component={InvoiceScreen} options={{ title: t('menu.invoice') }} />
        <Stack.Screen name="InvoiceForm" component={InvoiceFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="InvoiceMaterialService" component={InvoiceMaterialServiceScreen} options={{ title: t('menu.invoice_material_service') }} />
        <Stack.Screen name="InvoiceMaterialServiceForm" component={InvoiceMaterialServiceFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="ProductFamily" component={ProductFamilyScreen} options={{ title: t('menu.product_family') }} />
        <Stack.Screen name="ProductFamilyForm" component={ProductFamilyFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="IncidentType" component={IncidentTypeScreen} options={{ title: t('menu.incident_type') }} />
        <Stack.Screen name="IncidentTypeForm" component={IncidentTypeFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Incident" component={IncidentScreen} options={{ title: t('menu.incident') }} />
        <Stack.Screen name="IncidentForm" component={IncidentFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="IncidentDetail" component={IncidentDetailScreen} options={{ title: t('menu.incident_detail') }} />
        <Stack.Screen name="IncidentDetailForm" component={IncidentDetailFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Brand" component={BrandScreen} options={{ title: t('menu.brand') }} />
        <Stack.Screen name="BrandForm" component={BrandFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Unit" component={UnitScreen} options={{ title: t('menu.unit') }} />
        <Stack.Screen name="UnitForm" component={UnitFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Material" component={MaterialScreen} options={{ title: t('menu.material') }} />
        <Stack.Screen name="MaterialForm" component={MaterialFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="MaterialComponent" component={MaterialComponentScreen} options={{ title: t('menu.material_component') }} />
        <Stack.Screen name="MaterialComponentForm" component={MaterialComponentFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Movement" component={MovementScreen} options={{ title: t('menu.movement') }} />
        <Stack.Screen name="MovementForm" component={MovementFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="LocationType" component={LocationTypeScreen} options={{ title: t('menu.location_type') }} />
        <Stack.Screen name="LocationTypeForm" component={LocationTypeFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Location" component={LocationScreen} options={{ title: t('menu.location') }} />
        <Stack.Screen name="LocationForm" component={LocationFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Product" component={ProductScreen} options={{ title: t('menu.product') }} />
        <Stack.Screen name="ProductForm" component={ProductFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="NmIncidentProduct" component={NmIncidentProductScreen} options={{ title: t('menu.nm_incident_product') }} />
        <Stack.Screen name="NmIncidentProductForm" component={NmIncidentProductFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Task" component={TaskScreen} options={{ title: t('menu.task') }} />
        <Stack.Screen name="TaskForm" component={TaskFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="TaskNote" component={TaskNoteScreen} options={{ title: t('menu.task_note') }} />
        <Stack.Screen name="TaskNoteForm" component={TaskNoteFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Ticket" component={TicketScreen} options={{ title: t('menu.ticket') }} />
        <Stack.Screen name="TicketForm" component={TicketFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="FiscalAccount" component={FiscalAccountScreen} options={{ title: t('menu.fiscal_account') }} />
        <Stack.Screen name="FiscalAccountForm" component={FiscalAccountFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="FiscalStamp" component={FiscalStampScreen} options={{ title: t('menu.fiscal_stamp') }} />
        <Stack.Screen name="FiscalStampForm" component={FiscalStampFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="FiscalRecord" component={FiscalRecordScreen} options={{ title: t('menu.fiscal_record') }} />
        <Stack.Screen name="FiscalRecordForm" component={FiscalRecordFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Service" component={ServiceScreen} options={{ title: t('menu.service') }} />
        <Stack.Screen name="ServiceForm" component={ServiceFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Status" component={StatusScreen} options={{ title: t('menu.status') }} />
        <Stack.Screen name="StatusForm" component={StatusFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Theme" component={ThemeScreen} options={{ title: t('menu.theme') }} />
        <Stack.Screen name="ThemeForm" component={ThemeFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Department" component={DepartmentScreen} options={{ title: t('menu.department') }} />
        <Stack.Screen name="DepartmentForm" component={DepartmentFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Subdepartment" component={SubdepartmentScreen} options={{ title: t('menu.subdepartment') }} />
        <Stack.Screen name="SubdepartmentForm" component={SubdepartmentFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Level" component={LevelScreen} options={{ title: t('menu.level') }} />
        <Stack.Screen name="LevelForm" component={LevelFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Field" component={FieldScreen} options={{ title: t('menu.field') }} />
        <Stack.Screen name="FieldForm" component={FieldFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Permission" component={PermissionScreen} options={{ title: t('menu.permission') }} />
        <Stack.Screen name="PermissionForm" component={PermissionFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="NmFieldPermission" component={NmFieldPermissionScreen} options={{ title: t('menu.nm_field_permission') }} />
        <Stack.Screen name="NmFieldPermissionForm" component={NmFieldPermissionFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="EventLog" component={EventLogScreen} options={{ title: t('menu.event_log') }} />
        <Stack.Screen name="EventLogForm" component={EventLogFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="TaskType" component={TaskTypeScreen} options={{ title: t('menu.task_type') }} />
        <Stack.Screen name="TaskTypeForm" component={TaskTypeFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="Template" component={TemplateScreen} options={{ title: t('menu.template') }} />
        <Stack.Screen name="TemplateForm" component={TemplateFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="NmTemplateTask" component={NmTemplateTaskScreen} options={{ title: t('menu.nm_template_task') }} />
        <Stack.Screen name="NmTemplateTaskForm" component={NmTemplateTaskFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="SurveyQuestion" component={SurveyQuestionScreen} options={{ title: t('menu.survey_question') }} />
        <Stack.Screen name="SurveyQuestionForm" component={SurveyQuestionFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="SurveyMultipleAnswer" component={SurveyMultipleAnswerScreen} options={{ title: t('menu.survey_multiple_answer') }} />
        <Stack.Screen name="SurveyMultipleAnswerForm" component={SurveyMultipleAnswerFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="NmSurveyUser" component={NmSurveyUserScreen} options={{ title: t('menu.nm_survey_user') }} />
        <Stack.Screen name="NmSurveyUserForm" component={NmSurveyUserFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="EntityPermission" component={EntityPermissionScreen} options={{ title: t('menu.entity_permission') }} />
        <Stack.Screen name="EntityPermissionForm" component={EntityPermissionFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="InventoryStatus" component={InventoryStatusScreen} options={{ title: t('menu.inventory_status') }} />
        <Stack.Screen name="InventoryStatusForm" component={InventoryStatusFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="ProductSaleConfig" component={ProductSaleConfigScreen} options={{ title: t('menu.product_sale_config') }} />
        <Stack.Screen name="ProductSaleConfigForm" component={ProductSaleConfigFormScreen} options={{ title: t('common.newRecord') }} />
        <Stack.Screen name="PublicApiKey" component={PublicApiKeyScreen} options={{ title: t('menu.public_api_key') }} />
        <Stack.Screen name="PublicApiKeyForm" component={PublicApiKeyFormScreen} options={{ title: t('common.newRecord') }} />
        </>
      )}
    </Stack.Navigator>
  );
}
