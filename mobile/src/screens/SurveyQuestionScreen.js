import React from 'react';
import EntityListScreen from '../components/EntityListScreen';
import { validationRules } from '../utils/validation';

export function SurveyQuestionScreen({ navigation }) {
  return <EntityListScreen navigation={navigation} entity="survey_question" title="SurveyQuestion" pk="id_survey_question" fields={["question", "question_type", "owner"]} fieldTypes={{"question": "text", "question_type": "text", "owner": "number"}} validationRules={validationRules["survey_question"] || {}} />;
}
