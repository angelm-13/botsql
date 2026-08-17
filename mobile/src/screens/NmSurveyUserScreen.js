import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function NmSurveyUserScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="nm_survey_user" title="NmSurveyUser" pk="id_nm_survey_user" fields={["id_survey_question", "id_survey_multiple_answer", "id_user", "nm_survey_user_description", "score", "status"]} fieldTypes={{"id_survey_question": "number", "id_survey_multiple_answer": "number", "id_user": "number", "nm_survey_user_description": "text", "score": "number", "status": "number"}} validationRules={validationRules["nm_survey_user"] || {}} />;
}
