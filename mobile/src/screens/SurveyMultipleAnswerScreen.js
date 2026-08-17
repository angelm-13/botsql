import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function SurveyMultipleAnswerScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="survey_multiple_answer" title="SurveyMultipleAnswer" pk="id_survey_multiple_answer" fields={["id_survey_question", "survey_answer_description", "score"]} fieldTypes={{"id_survey_question": "number", "survey_answer_description": "text", "score": "number"}} validationRules={validationRules["survey_multiple_answer"] || {}} />;
}
