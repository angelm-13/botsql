import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../auth/AuthContext';
import { t } from '../i18n';
import { theme } from '../theme';

export default function HomeScreen({ navigation }) {
  const { logout } = useAuth();
  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.header}>
        <View>
          <Text style={styles.kicker}>ERP · CRM · SCM</Text>
          <Text style={styles.title}>Control empresarial</Text>
        </View>
        <Pressable onPress={logout} style={styles.logout}><Text style={styles.logoutText}>{t('common.logout')}</Text></Pressable>
      </View>
      <View style={styles.grid}>
        <Pressable style={styles.card} onPress={() => navigation.navigate('User')}><Text style={styles.cardTitle}>{t('menu.user')}</Text><Text style={styles.cardMeta}>user</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('UserMfa')}><Text style={styles.cardTitle}>{t('menu.user_mfa')}</Text><Text style={styles.cardMeta}>user_mfa</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('PayrollPeriod')}><Text style={styles.cardTitle}>{t('menu.payroll_period')}</Text><Text style={styles.cardMeta}>payroll_period</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('PayrollDetail')}><Text style={styles.cardTitle}>{t('menu.payroll_detail')}</Text><Text style={styles.cardMeta}>payroll_detail</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('PayrollConcept')}><Text style={styles.cardTitle}>{t('menu.payroll_concept')}</Text><Text style={styles.cardMeta}>payroll_concept</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('PayrollMovement')}><Text style={styles.cardTitle}>{t('menu.payroll_movement')}</Text><Text style={styles.cardMeta}>payroll_movement</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('CustomerSupplier')}><Text style={styles.cardTitle}>{t('menu.customer_supplier')}</Text><Text style={styles.cardMeta}>customer_supplier</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Proyect')}><Text style={styles.cardTitle}>{t('menu.proyect')}</Text><Text style={styles.cardMeta}>proyect</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Bank')}><Text style={styles.cardTitle}>{t('menu.bank')}</Text><Text style={styles.cardMeta}>bank</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('BankAccount')}><Text style={styles.cardTitle}>{t('menu.bank_account')}</Text><Text style={styles.cardMeta}>bank_account</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Invoice')}><Text style={styles.cardTitle}>{t('menu.invoice')}</Text><Text style={styles.cardMeta}>invoice</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('InvoiceMaterialService')}><Text style={styles.cardTitle}>{t('menu.invoice_material_service')}</Text><Text style={styles.cardMeta}>invoice_material_service</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('ProductFamily')}><Text style={styles.cardTitle}>{t('menu.product_family')}</Text><Text style={styles.cardMeta}>product_family</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('IncidentType')}><Text style={styles.cardTitle}>{t('menu.incident_type')}</Text><Text style={styles.cardMeta}>incident_type</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Incident')}><Text style={styles.cardTitle}>{t('menu.incident')}</Text><Text style={styles.cardMeta}>incident</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('IncidentDetail')}><Text style={styles.cardTitle}>{t('menu.incident_detail')}</Text><Text style={styles.cardMeta}>incident_detail</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Brand')}><Text style={styles.cardTitle}>{t('menu.brand')}</Text><Text style={styles.cardMeta}>brand</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Unit')}><Text style={styles.cardTitle}>{t('menu.unit')}</Text><Text style={styles.cardMeta}>unit</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Material')}><Text style={styles.cardTitle}>{t('menu.material')}</Text><Text style={styles.cardMeta}>material</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('MaterialComponent')}><Text style={styles.cardTitle}>{t('menu.material_component')}</Text><Text style={styles.cardMeta}>material_component</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Movement')}><Text style={styles.cardTitle}>{t('menu.movement')}</Text><Text style={styles.cardMeta}>movement</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('LocationType')}><Text style={styles.cardTitle}>{t('menu.location_type')}</Text><Text style={styles.cardMeta}>location_type</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Location')}><Text style={styles.cardTitle}>{t('menu.location')}</Text><Text style={styles.cardMeta}>location</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Product')}><Text style={styles.cardTitle}>{t('menu.product')}</Text><Text style={styles.cardMeta}>product</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('NmIncidentProduct')}><Text style={styles.cardTitle}>{t('menu.nm_incident_product')}</Text><Text style={styles.cardMeta}>nm_incident_product</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Task')}><Text style={styles.cardTitle}>{t('menu.task')}</Text><Text style={styles.cardMeta}>task</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('TaskNote')}><Text style={styles.cardTitle}>{t('menu.task_note')}</Text><Text style={styles.cardMeta}>task_note</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Ticket')}><Text style={styles.cardTitle}>{t('menu.ticket')}</Text><Text style={styles.cardMeta}>ticket</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('FiscalAccount')}><Text style={styles.cardTitle}>{t('menu.fiscal_account')}</Text><Text style={styles.cardMeta}>fiscal_account</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('FiscalStamp')}><Text style={styles.cardTitle}>{t('menu.fiscal_stamp')}</Text><Text style={styles.cardMeta}>fiscal_stamp</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('FiscalRecord')}><Text style={styles.cardTitle}>{t('menu.fiscal_record')}</Text><Text style={styles.cardMeta}>fiscal_record</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Service')}><Text style={styles.cardTitle}>{t('menu.service')}</Text><Text style={styles.cardMeta}>service</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Status')}><Text style={styles.cardTitle}>{t('menu.status')}</Text><Text style={styles.cardMeta}>status</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Theme')}><Text style={styles.cardTitle}>{t('menu.theme')}</Text><Text style={styles.cardMeta}>theme</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Department')}><Text style={styles.cardTitle}>{t('menu.department')}</Text><Text style={styles.cardMeta}>department</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Subdepartment')}><Text style={styles.cardTitle}>{t('menu.subdepartment')}</Text><Text style={styles.cardMeta}>subdepartment</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Level')}><Text style={styles.cardTitle}>{t('menu.level')}</Text><Text style={styles.cardMeta}>level</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Field')}><Text style={styles.cardTitle}>{t('menu.field')}</Text><Text style={styles.cardMeta}>field</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Permission')}><Text style={styles.cardTitle}>{t('menu.permission')}</Text><Text style={styles.cardMeta}>permission</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('NmFieldPermission')}><Text style={styles.cardTitle}>{t('menu.nm_field_permission')}</Text><Text style={styles.cardMeta}>nm_field_permission</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('EventLog')}><Text style={styles.cardTitle}>{t('menu.event_log')}</Text><Text style={styles.cardMeta}>event_log</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('TaskType')}><Text style={styles.cardTitle}>{t('menu.task_type')}</Text><Text style={styles.cardMeta}>task_type</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('Template')}><Text style={styles.cardTitle}>{t('menu.template')}</Text><Text style={styles.cardMeta}>template</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('NmTemplateTask')}><Text style={styles.cardTitle}>{t('menu.nm_template_task')}</Text><Text style={styles.cardMeta}>nm_template_task</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('SurveyQuestion')}><Text style={styles.cardTitle}>{t('menu.survey_question')}</Text><Text style={styles.cardMeta}>survey_question</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('SurveyMultipleAnswer')}><Text style={styles.cardTitle}>{t('menu.survey_multiple_answer')}</Text><Text style={styles.cardMeta}>survey_multiple_answer</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('NmSurveyUser')}><Text style={styles.cardTitle}>{t('menu.nm_survey_user')}</Text><Text style={styles.cardMeta}>nm_survey_user</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('EntityPermission')}><Text style={styles.cardTitle}>{t('menu.entity_permission')}</Text><Text style={styles.cardMeta}>entity_permission</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('InventoryStatus')}><Text style={styles.cardTitle}>{t('menu.inventory_status')}</Text><Text style={styles.cardMeta}>inventory_status</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('ProductSaleConfig')}><Text style={styles.cardTitle}>{t('menu.product_sale_config')}</Text><Text style={styles.cardMeta}>product_sale_config</Text></Pressable>
        <Pressable style={styles.card} onPress={() => navigation.navigate('PublicApiKey')}><Text style={styles.cardTitle}>{t('menu.public_api_key')}</Text><Text style={styles.cardMeta}>public_api_key</Text></Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: 18, gap: 16 },
  header: { flexDirection: 'row', justifyContent: 'space-between', gap: 12, alignItems: 'center' },
  kicker: { color: theme.colors.primary, fontWeight: '900', letterSpacing: 1 },
  title: { color: theme.colors.ink, fontSize: 28, fontWeight: '900', marginTop: 4 },
  logout: { borderWidth: 1, borderColor: theme.colors.border, paddingVertical: 10, paddingHorizontal: 12, borderRadius: 14, backgroundColor: '#fff' },
  logoutText: { color: theme.colors.ink, fontWeight: '800' },
  grid: { gap: 12 },
  card: { backgroundColor: '#fff', borderRadius: 20, padding: 18, borderWidth: 1, borderColor: theme.colors.border, ...theme.shadow },
  cardTitle: { color: theme.colors.ink, fontWeight: '900', fontSize: 18 },
  cardMeta: { color: theme.colors.muted, marginTop: 6 },
});
