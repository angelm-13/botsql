export const validationRules = {
  "user": {
    "email": [
      {
        "validation_type": "format",
        "rule": "email:rfc5322",
        "message_key": "validations.user.email.email",
        "severity": "error",
        "graphql_error_code": "INVALID_EMAIL"
      }
    ],
    "id_permission": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.user.id_permission.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_proyect": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.user.id_proyect.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "principal_phone": [
      {
        "validation_type": "format",
        "rule": "phone:e164_or_local",
        "message_key": "validations.user.principal_phone.phone",
        "severity": "warning",
        "graphql_error_code": "INVALID_PHONE"
      }
    ],
    "secundary_phone": [
      {
        "validation_type": "format",
        "rule": "phone:e164_or_local",
        "message_key": "validations.user.secundary_phone.phone",
        "severity": "warning",
        "graphql_error_code": "INVALID_PHONE"
      }
    ],
    "supervisor": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.user.supervisor.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "base_salary": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.user.base_salary.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "id_status": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.user.id_status.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "tax_id": [
      {
        "validation_type": "format",
        "rule": "mx_rfc_or_tax_id",
        "message_key": "validations.user.tax_id.tax_id",
        "severity": "error",
        "graphql_error_code": "INVALID_TAX_ID"
      }
    ],
    "password": [
      {
        "validation_type": "format",
        "rule": "password:min8:upper:lower:number:special",
        "message_key": "validations.user.password.strong",
        "severity": "error",
        "graphql_error_code": "STRONG"
      }
    ],
    "full_name": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.user.full_name.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "user_mfa": {
    "id_user": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.user_mfa.id_user.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "secret": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.user_mfa.secret.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "secret_iv": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.user_mfa.secret_iv.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "enabled": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.user_mfa.enabled.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "failed_attempts": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.user_mfa.failed_attempts.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "payroll_period": {
    "id_status": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.payroll_period.id_status.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "period_end": [
      {
        "validation_type": "comparison",
        "rule": "period_end >= period_start",
        "message_key": "validations.payroll_period.period_end.after_start",
        "severity": "error",
        "graphql_error_code": "AFTER_START"
      }
    ]
  },
  "payroll_detail": {
    "id_payroll_period": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.payroll_detail.id_payroll_period.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      },
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.payroll_detail.id_payroll_period.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "id_user": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.payroll_detail.id_user.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "gross_salary": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.payroll_detail.gross_salary.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "total_earnings": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.payroll_detail.total_earnings.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "total_deductions": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.payroll_detail.total_deductions.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "net_pay": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.payroll_detail.net_pay.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ]
  },
  "payroll_concept": {
    "is_taxable": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.payroll_concept.is_taxable.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "is_imss": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.payroll_concept.is_imss.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "payroll_concept_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.payroll_concept.payroll_concept_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "payroll_movement": {
    "id_payroll_detail": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.payroll_movement.id_payroll_detail.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      },
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.payroll_movement.id_payroll_detail.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "id_payroll_concept": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.payroll_movement.id_payroll_concept.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      },
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.payroll_movement.id_payroll_concept.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "amount": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.payroll_movement.amount.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ]
  },
  "customer_supplier": {
    "phone": [
      {
        "validation_type": "format",
        "rule": "phone:e164_or_local",
        "message_key": "validations.customer_supplier.phone.phone",
        "severity": "warning",
        "graphql_error_code": "INVALID_PHONE"
      }
    ],
    "email": [
      {
        "validation_type": "format",
        "rule": "email:rfc5322",
        "message_key": "validations.customer_supplier.email.email",
        "severity": "error",
        "graphql_error_code": "INVALID_EMAIL"
      }
    ],
    "tax_id": [
      {
        "validation_type": "format",
        "rule": "mx_rfc_or_tax_id",
        "message_key": "validations.customer_supplier.tax_id.tax_id",
        "severity": "error",
        "graphql_error_code": "INVALID_TAX_ID"
      }
    ],
    "id_user": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.customer_supplier.id_user.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "name": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.customer_supplier.name.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "proyect": {
    "id_customer_supplier": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.proyect.id_customer_supplier.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "leader": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.proyect.leader.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "proyect_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.proyect.proyect_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "bank": {
    "bank_name": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.bank.bank_name.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "bank_account": {
    "id_bank": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.bank_account.id_bank.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "bank_account_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.bank_account.bank_account_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "invoice": {
    "date_expiration": [
      {
        "validation_type": "comparison",
        "rule": "date_expiration >= date_emision",
        "message_key": "validations.invoice.date_expiration.after_emision",
        "severity": "error",
        "graphql_error_code": "INVALID_DATE_RANGE"
      }
    ],
    "subtotal": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.invoice.subtotal.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "tax": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.invoice.tax.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "total": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.invoice.total.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      },
      {
        "validation_type": "business",
        "rule": "total = subtotal + tax",
        "message_key": "validations.invoice.total.matches_subtotal_tax",
        "severity": "error",
        "graphql_error_code": "MATCHES_SUBTOTAL_TAX"
      }
    ],
    "id_customer_supplier": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice.id_customer_supplier.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "tax_certification_supplier": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice.tax_certification_supplier.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      },
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.invoice.tax_certification_supplier.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "id_status": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice.id_status.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_issuer_customer_supplier": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice.id_issuer_customer_supplier.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "apply_tax": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice.apply_tax.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "tax_rate": [
      {
        "validation_type": "range",
        "rule": "value >= 0 and value <= 100",
        "message_key": "validations.invoice.tax_rate.percent_range",
        "severity": "error",
        "graphql_error_code": "INVALID_PERCENT"
      }
    ]
  },
  "invoice_material_service": {
    "id_invoice": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice_material_service.id_invoice.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "is_directly_related_to_product_service_creation": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice_material_service.is_directly_related_to_product_service_creation.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_authorized": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice_material_service.id_authorized.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_status": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice_material_service.id_status.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_buyer": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice_material_service.id_buyer.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_customer_supplier": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice_material_service.id_customer_supplier.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "gross_price": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.invoice_material_service.gross_price.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "quantity": [
      {
        "validation_type": "range",
        "rule": "value > 0",
        "message_key": "validations.invoice_material_service.quantity.positive",
        "severity": "error",
        "graphql_error_code": "INVALID_QUANTITY"
      }
    ],
    "invoice_material_service_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice_material_service.invoice_material_service_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "line_type": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice_material_service.line_type.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "tax_applicable": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice_material_service.tax_applicable.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "line_tax": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.invoice_material_service.line_tax.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "line_total": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.invoice_material_service.line_total.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "authorization_status": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.invoice_material_service.authorization_status.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "product_family": {
    "product_family_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.product_family.product_family_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "incident_type": {
    "incident_type_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.incident_type.incident_type_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "incident": {
    "id_incident_type": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.incident.id_incident_type.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_user": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.incident.id_user.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "incident_detail": {
    "id_incident_type": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.incident_detail.id_incident_type.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "incident_detail_name": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.incident_detail.incident_detail_name.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "incident_detail_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.incident_detail.incident_detail_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "brand": {
    "brand_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.brand.brand_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "unit": {
    "is_active": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.unit.is_active.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "measurement_system": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.unit.measurement_system.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "unit_name": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.unit.unit_name.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "material": {
    "id_unit": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.material.id_unit.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_brand": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.material.id_brand.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_product_family": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.material.id_product_family.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "material_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.material.material_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "material_component": {
    "id_material": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.material_component.id_material.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_component": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.material_component.id_component.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      },
      {
        "validation_type": "business",
        "rule": "id_component != id_material",
        "message_key": "validations.material_component.no_self_component",
        "severity": "error",
        "graphql_error_code": "NO_SELF_COMPONENT"
      }
    ],
    "id_unit": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.material_component.id_unit.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "movement": {
    "id_fiscal_account": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.movement.id_fiscal_account.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "amount": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.movement.amount.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ]
  },
  "location_type": {
    "location_type_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.location_type.location_type_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "location": {
    "id_location_type": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.location.id_location_type.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_location_reference": [
      {
        "validation_type": "business",
        "rule": "id_location_reference != id_location",
        "message_key": "validations.location.no_self_parent",
        "severity": "error",
        "graphql_error_code": "NO_SELF_PARENT"
      }
    ],
    "location_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.location.location_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "product": {
    "id_location": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.product.id_location.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_material": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.product.id_material.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "gross_price": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.product.gross_price.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "is_directly_related_to_product_service": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.product.is_directly_related_to_product_service.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "nm_incident_product": {
    "id_incident": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_incident_product.id_incident.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_product": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_incident_product.id_product.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "quantity": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_incident_product.quantity.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      },
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.nm_incident_product.quantity.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ]
  },
  "task": {
    "id_proyect": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.task.id_proyect.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "task_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.task.task_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "task_note": {
    "id_task": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.task_note.id_task.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "task_note_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.task_note.task_note_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "ticket": {
    "ticket_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.ticket.ticket_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "fiscal_account": {
    "balance": [
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.fiscal_account.balance.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "fiscal_account_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.fiscal_account.fiscal_account_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "fiscal_stamp": {
    "concept": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.fiscal_stamp.concept.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "reviewed_by": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.fiscal_stamp.reviewed_by.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "authorized_by": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.fiscal_stamp.authorized_by.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "num_policy": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.fiscal_stamp.num_policy.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "fiscal_record": {
    "fiscal_record_name": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.fiscal_record.fiscal_record_name.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_fiscal_account": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.fiscal_record.id_fiscal_account.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "amount": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.fiscal_record.amount.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      },
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.fiscal_record.amount.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "id_fiscal_stamp": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.fiscal_record.id_fiscal_stamp.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "service": {
    "service_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.service.service_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_brand": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.service.id_brand.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "status": {
    "status_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.status.status_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "category": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.status.category.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "is_terminal": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.status.is_terminal.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "theme": {
    "tenant_id": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.theme.tenant_id.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "primary_color": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.theme.primary_color.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "secondary_color": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.theme.secondary_color.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "background_color": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.theme.background_color.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "text_color": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.theme.text_color.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "highlight_color": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.theme.highlight_color.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "success_color": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.theme.success_color.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "error_color": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.theme.error_color.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "department": {
    "department_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.department.department_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "subdepartment": {
    "id_department": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.subdepartment.id_department.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "subdepartment_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.subdepartment.subdepartment_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "level": {
    "level_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.level.level_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "field": {
    "table_name": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.field.table_name.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "field_name": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.field.field_name.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "permission": {
    "authorized_by": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.permission.authorized_by.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_department": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.permission.id_department.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_subdepartment": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.permission.id_subdepartment.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_level": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.permission.id_level.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "permission_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.permission.permission_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "nm_field_permission": {
    "id_field": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_field_permission.id_field.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_permission": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_field_permission.id_permission.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "control_type": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_field_permission.control_type.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "event_log": {
    "table_name": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.event_log.table_name.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "field_name": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.event_log.field_name.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "action": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.event_log.action.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "before_value": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.event_log.before_value.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "after_value": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.event_log.after_value.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "task_type": {
    "task_type_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.task_type.task_type_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "template": {
    "template_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.template.template_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "nm_template_task": {
    "id_task": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_template_task.id_task.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_template": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_template_task.id_template.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "survey_question": {
    "question": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.survey_question.question.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "question_type": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.survey_question.question_type.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "owner": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.survey_question.owner.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "survey_multiple_answer": {
    "id_survey_question": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.survey_multiple_answer.id_survey_question.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "survey_answer_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.survey_multiple_answer.survey_answer_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "nm_survey_user": {
    "id_survey_question": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_survey_user.id_survey_question.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_survey_multiple_answer": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_survey_user.id_survey_multiple_answer.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_user": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_survey_user.id_user.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "nm_survey_user_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_survey_user.nm_survey_user_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "status": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.nm_survey_user.status.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "entity_permission": {
    "id_permission": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.entity_permission.id_permission.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "entity_name": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.entity_permission.entity_name.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "scope_create": [
      {
        "validation_type": "range",
        "rule": "value >= 0 and value <= 7",
        "message_key": "validations.entity_permission.scope_create.range",
        "severity": "error",
        "graphql_error_code": "INVALID_PERMISSION_SCOPE"
      }
    ],
    "scope_read": [
      {
        "validation_type": "range",
        "rule": "value >= 0 and value <= 7",
        "message_key": "validations.entity_permission.scope_read.range",
        "severity": "error",
        "graphql_error_code": "INVALID_PERMISSION_SCOPE"
      }
    ],
    "scope_update": [
      {
        "validation_type": "range",
        "rule": "value >= 0 and value <= 7",
        "message_key": "validations.entity_permission.scope_update.range",
        "severity": "error",
        "graphql_error_code": "INVALID_PERMISSION_SCOPE"
      }
    ],
    "scope_delete": [
      {
        "validation_type": "range",
        "rule": "value >= 0 and value <= 7",
        "message_key": "validations.entity_permission.scope_delete.range",
        "severity": "error",
        "graphql_error_code": "INVALID_PERMISSION_SCOPE"
      }
    ]
  },
  "inventory_status": {
    "inventory_status_code": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.inventory_status.inventory_status_code.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "inventory_status_description": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.inventory_status.inventory_status_description.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "color": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.inventory_status.color.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "entity_scope": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.inventory_status.entity_scope.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "flow_scope": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.inventory_status.flow_scope.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_department": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.inventory_status.id_department.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_minimum_level": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.inventory_status.id_minimum_level.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "is_active": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.inventory_status.is_active.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "is_terminal": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.inventory_status.is_terminal.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "visible_to_other_departments": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.inventory_status.visible_to_other_departments.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "sort_order": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.inventory_status.sort_order.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      },
      {
        "validation_type": "range",
        "rule": "value >= 0",
        "message_key": "validations.inventory_status.sort_order.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ]
  },
  "product_sale_config": {
    "id_product": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.product_sale_config.id_product.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "id_inventory_status": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.product_sale_config.id_inventory_status.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "margin_percent": [
      {
        "validation_type": "range",
        "rule": "value is null or value == \"\" or (value >= 0 and value <= 100)",
        "message_key": "validations.product_sale_config.margin_percent.percent_range",
        "severity": "error",
        "graphql_error_code": "INVALID_PERCENT"
      }
    ],
    "manual_price": [
      {
        "validation_type": "range",
        "rule": "value is null or value == \"\" or value >= 0",
        "message_key": "validations.product_sale_config.manual_price.non_negative",
        "severity": "error",
        "graphql_error_code": "NEGATIVE_VALUE"
      }
    ],
    "is_active": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.product_sale_config.is_active.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  },
  "public_api_key": {
    "label": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.public_api_key.label.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "key_hash": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.public_api_key.key_hash.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "key_prefix": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.public_api_key.key_prefix.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "allowed_domains": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.public_api_key.allowed_domains.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ],
    "rate_limit_per_min": [
      {
        "validation_type": "range",
        "rule": "value >= 1",
        "message_key": "validations.public_api_key.rate_limit_per_min.positive",
        "severity": "error",
        "graphql_error_code": "INVALID_RATE_LIMIT"
      }
    ],
    "is_active": [
      {
        "validation_type": "required",
        "rule": "value is not null and value != \"\"",
        "message_key": "validations.public_api_key.is_active.required",
        "severity": "error",
        "graphql_error_code": "REQUIRED_FIELD"
      }
    ]
  }
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^\+?[0-9][0-9\s().-]{6,19}$/;
const MX_TAX_ID_RE = /^[A-ZÑ&]{3,4}[0-9]{6}[A-Z0-9]{3}$/i;

function isEmpty(value) {
  return value === null || value === undefined || (typeof value === "string" && value.trim() === "");
}

function fail(errors, field, rule) {
  if (!errors[field]) errors[field] = rule.message_key || "errors.validation_failed";
}

function toNumber(value) {
  if (isEmpty(value)) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function toComparable(value) {
  const number = toNumber(value);
  if (number !== null) return number;
  if (isEmpty(value)) return null;
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? null : timestamp;
}

function compare(left, operator, right) {
  if (left === null || right === null) return true;
  if (operator === ">=") return left >= right;
  if (operator === "<=") return left <= right;
  if (operator === ">") return left > right;
  if (operator === "<") return left < right;
  if (operator === "=" || operator === "==") return left === right;
  if (operator === "!=") return left !== right;
  return true;
}

function validateRequired(errors, field, payload, rule) {
  if (isEmpty(payload[field])) fail(errors, field, rule);
}

function validateRange(errors, field, payload, rule) {
  const value = toNumber(payload[field]);
  if (value === null) return;
  const match = String(rule.rule || "").match(/value\s*(>=|<=|>|<|=|==|!=)\s*(-?\d+(?:\.\d+)?)/);
  if (!match) return;
  const [, operator, rawLimit] = match;
  if (!compare(value, operator, Number(rawLimit))) fail(errors, field, rule);
}

function validateFormat(errors, field, payload, rule) {
  if (isEmpty(payload[field])) return;
  const text = String(payload[field]).trim();
  const ruleText = String(rule.rule || "").toLowerCase();
  if (ruleText.startsWith("email") && !EMAIL_RE.test(text)) fail(errors, field, rule);
  if (ruleText.startsWith("phone") && !PHONE_RE.test(text)) fail(errors, field, rule);
  if ((ruleText.includes("mx_rfc") || ruleText.includes("tax_id")) && !MX_TAX_ID_RE.test(text)) fail(errors, field, rule);
  if (ruleText.startsWith("password")) {
    const checks = {
      min8: text.length >= 8,
      upper: /[A-Z]/.test(text),
      lower: /[a-z]/.test(text),
      number: /\d/.test(text),
      special: /[^A-Za-z0-9]/.test(text),
    };
    if (Object.entries(checks).some(([token, ok]) => ruleText.includes(token) && !ok)) fail(errors, field, rule);
  }
}

function validateComparison(errors, field, payload, rule) {
  const match = String(rule.rule || "").match(/(\w+)\s*(>=|<=|>|<|=|==|!=)\s*(\w+)/);
  if (!match) return;
  const [, leftField, operator, rightField] = match;
  const left = toComparable(payload[leftField]);
  const right = toComparable(payload[rightField]);
  if (!compare(left, operator, right)) fail(errors, field, rule);
}

function validateBusiness(errors, field, payload, rule) {
  const ruleText = String(rule.rule || "");
  const sumMatch = ruleText.match(/(\w+)\s*=\s*(\w+)\s*\+\s*(\w+)/);
  if (sumMatch) {
    const [, targetField, leftField, rightField] = sumMatch;
    const target = toNumber(payload[targetField]);
    const left = toNumber(payload[leftField]);
    const right = toNumber(payload[rightField]);
    if (target !== null && left !== null && right !== null && target !== left + right) fail(errors, field, rule);
    return;
  }
  const neqMatch = ruleText.match(/(\w+)\s*!=\s*(\w+)/);
  if (neqMatch) {
    const [, leftField, rightField] = neqMatch;
    if (!isEmpty(payload[leftField]) && !isEmpty(payload[rightField]) && payload[leftField] === payload[rightField]) fail(errors, field, rule);
    return;
  }
  if (ruleText.includes("cannot equal") && ruleText.includes("id_task")) {
    if (!isEmpty(payload.dependency) && !isEmpty(payload.id_task) && payload.dependency === payload.id_task) fail(errors, field, rule);
  }
}

export function validateForm(entity, payload, rulesByField = validationRules[entity] || {}) {
  const errors = {};
  Object.entries(rulesByField || {}).forEach(([field, rules]) => {
    (rules || []).forEach((rule) => {
      const type = rule.validation_type;
      if (type === "required") validateRequired(errors, field, payload, rule);
      else if (type === "range") validateRange(errors, field, payload, rule);
      else if (type === "format") validateFormat(errors, field, payload, rule);
      else if (type === "comparison") validateComparison(errors, field, payload, rule);
      else if (type === "business") validateBusiness(errors, field, payload, rule);
    });
  });
  return { valid: Object.keys(errors).length === 0, errors };
}

export function inputPropsForField(field, rules = [], inputType = "text") {
  const ruleText = `${field} ${(rules || []).map((rule) => rule.rule || "").join(" ")}`.toLowerCase();
  const props = {};
  if (inputType !== "checkbox" && (rules || []).some((rule) => rule.validation_type === "required")) props.required = true;
  (rules || []).forEach((rule) => {
    const match = String(rule.rule || "").match(/value\s*(>=|<=|>|<|=|==|!=)\s*(-?\d+(?:\.\d+)?)/);
    if (!match) return;
    const [, operator, rawLimit] = match;
    if (operator === ">=" || operator === ">") props.min = rawLimit;
    if (operator === "<=" || operator === "<") props.max = rawLimit;
  });
  if (inputType === "number") {
    props.inputMode = "decimal";
    props.step = "any";
  }
  if (ruleText.includes("email")) props.inputMode = "email";
  if (ruleText.includes("phone") || ruleText.includes("tel")) props.inputMode = "tel";
  if (ruleText.includes("password")) props.autoComplete = "new-password";
  if (ruleText.includes("mx_rfc") || ruleText.includes("tax_id") || field.includes("rfc")) props.autoCapitalize = "characters";
  return props;
}
