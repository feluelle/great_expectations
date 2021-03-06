import logging
from copy import deepcopy

from six import integer_types

from great_expectations.render.renderer.content_block.expectation_string import (
    ExpectationStringRenderer,
)
from great_expectations.render.types import (
    RenderedContentBlockContainer,
    RenderedStringTemplateContent,
    RenderedTableContent,
    CollapseContent)
from great_expectations.render.util import num_to_str

logger = logging.getLogger(__name__)


class ValidationResultsTableContentBlockRenderer(ExpectationStringRenderer):
    _content_block_type = "table"
    _rendered_component_type = RenderedTableContent

    _default_element_styling = {
        "default": {
            "classes": ["badge", "badge-secondary"]
        },
        "params": {
            "column": {
                "classes": ["badge", "badge-primary"]
            }
        }
    }

    _default_content_block_styling = {
        "body": {
            "classes": ["table"],
        },
        "classes": ["ml-2", "mr-2", "mt-0", "mb-0", "table-responsive"],
    }

    @classmethod
    def _get_status_icon(cls, evr):
        if evr.exception_info["raised_exception"]:
            return RenderedStringTemplateContent(**{
                "content_block_type": "string_template",
                "string_template": {
                    "template": "$icon",
                    "params": {"icon": ""},
                    "styling": {
                        "params": {
                            "icon": {
                                "classes": ["fas", "fa-exclamation-triangle", "text-warning"],
                                "tag": "i"
                            }
                        }
                    }
                }
            })

        if evr.success:
            return RenderedStringTemplateContent(**{
                "content_block_type": "string_template",
                "string_template": {
                    "template": "$icon",
                    "params": {"icon": ""},
                    "styling": {
                        "params": {
                            "icon": {
                                "classes": ["fas", "fa-check-circle", "text-success"],
                                "tag": "i"
                            }
                        }
                    }
                },
                "styling": {
                    "parent": {
                        "classes": ["hide-succeeded-validation-target-child"]
                    }
                }
            })
        else:
            return RenderedStringTemplateContent(**{
                "content_block_type": "string_template",
                "string_template": {
                    "template": "$icon",
                    "params": {"icon": ""},
                    "styling": {
                        "params": {
                            "icon": {
                                "tag": "i",
                                "classes": ["fas", "fa-times", "text-danger"]
                            }
                        }
                    }
                }
            })

    @classmethod
    def _get_unexpected_table(cls, evr):
        try:
            result = evr.result
        except KeyError:
            return None

        if result is None:
            return None

        if not result.get("partial_unexpected_list") and not result.get("partial_unexpected_counts"):
            return None

        table_rows = []

        if result.get("partial_unexpected_counts"):
            header_row = ["Unexpected Value", "Count"]
            for unexpected_count in result.get("partial_unexpected_counts"):
                if unexpected_count.get("value"):
                    table_rows.append([unexpected_count.get("value"), unexpected_count.get("count")])
                elif unexpected_count.get("value") == "":
                    table_rows.append(["EMPTY", unexpected_count.get("count")])
                elif unexpected_count.get("value") is not None:
                    table_rows.append([unexpected_count.get("value"), unexpected_count.get("count")])
                else:
                    table_rows.append(["null", unexpected_count.get("count")])
        else:
            header_row = ["Unexpected Value"]
            for unexpected_value in result.get("partial_unexpected_list"):
                if unexpected_value:
                    table_rows.append([unexpected_value])
                elif unexpected_value == "":
                    table_rows.append(["EMPTY"])
                elif unexpected_value is not None:
                    table_rows.append([unexpected_value])
                else:
                    table_rows.append(["null"])

        unexpected_table_content_block = RenderedTableContent(**{
            "content_block_type": "table",
            "table": table_rows,
            "header_row": header_row,
            "styling": {
                "body": {
                    "classes": ["table-bordered", "table-sm", "mt-3"]
                }
            }
        })

        return unexpected_table_content_block

    @classmethod
    def _get_unexpected_statement(cls, evr):
        success = evr.success
        result = evr.result

        if evr.exception_info["raised_exception"]:
            exception_message_template_str = "\n\n$expectation_type raised an exception:\n$exception_message"

            exception_message = RenderedStringTemplateContent(**{
                "content_block_type": "string_template",
                "string_template": {
                    "template": exception_message_template_str,
                    "params": {
                        "expectation_type": evr.expectation_config.expectation_type,
                        "exception_message": evr.exception_info["exception_message"]
                    },
                    "tag": "strong",
                    "styling": {
                        "classes": ["text-danger"],
                        "params": {
                            "exception_message": {
                                "tag": "code"
                            },
                            "expectation_type": {
                                "classes": ["badge", "badge-danger", "mb-2"]
                            }
                        }
                    }
                },
            })

            exception_traceback_collapse = CollapseContent(**{
                "collapse_toggle_link": "Show exception traceback...",
                "collapse": [
                    RenderedStringTemplateContent(**{
                        "content_block_type": "string_template",
                        "string_template": {
                            "template": evr.exception_info["exception_traceback"],
                            "tag": "code"
                        }
                    })
                ]
            })

            return [exception_message, exception_traceback_collapse]

        if success or not result.get("unexpected_count"):
            return []
        else:
            unexpected_count = num_to_str(result["unexpected_count"], use_locale=True, precision=20)
            unexpected_percent = num_to_str(result["unexpected_percent"], precision=4) + "%"
            element_count = num_to_str(result["element_count"], use_locale=True, precision=20)

            template_str = "\n\n$unexpected_count unexpected values found. " \
                           "$unexpected_percent of $element_count total rows."

            return [
                RenderedStringTemplateContent(**{
                "content_block_type": "string_template",
                "string_template": {
                    "template": template_str,
                    "params": {
                        "unexpected_count": unexpected_count,
                        "unexpected_percent": unexpected_percent,
                        "element_count": element_count
                    },
                    "tag": "strong",
                    "styling": {
                        "classes": ["text-danger"]
                    }
                }})
            ]

    @classmethod
    def _get_kl_divergence_observed_value(cls, evr):
        if not evr.result.get("details"):
            return "--"

        observed_partition_object = evr.result["details"]["observed_partition"]
        observed_distribution = super(
            ValidationResultsTableContentBlockRenderer, cls)._get_kl_divergence_chart(observed_partition_object)

        observed_value = num_to_str(evr.result.get("observed_value")) if evr.result.get("observed_value") \
            else evr.result.get("observed_value")

        observed_value_content_block = RenderedStringTemplateContent(**{
            "content_block_type": "string_template",
            "string_template": {
                "template": "KL Divergence: $observed_value",
                "params": {
                    "observed_value": str(
                        observed_value) if observed_value else "None (-infinity, infinity, or NaN)",
                },
                "styling": {
                    "classes": ["mb-2"]
                }
            },
        })

        return RenderedContentBlockContainer(**{
            "content_block_type": "content_block_container",
            "content_blocks": [
                observed_value_content_block,
                observed_distribution
            ]
        })

    @classmethod
    def _get_quantile_values_observed_value(cls, evr):
        if evr.result is None or evr.result.get("observed_value") is None:
            return "--"

        quantiles = evr.result.get("observed_value", {}).get("quantiles", [])
        value_ranges = evr.result.get("observed_value", {}).get("values", [])

        table_header_row = ["Quantile", "Value"]
        table_rows = []

        quantile_strings = {
            .25: "Q1",
            .75: "Q3",
            .50: "Median"
        }

        for idx, quantile in enumerate(quantiles):
            quantile_string = quantile_strings.get(quantile)
            table_rows.append([
                quantile_string if quantile_string else "{:3.2f}".format(quantile),
                str(value_ranges[idx])
            ])

        return RenderedTableContent(**{
            "content_block_type": "table",
            "header_row": table_header_row,
            "table": table_rows,
            "styling": {
                "body": {
                    "classes": ["table", "table-sm", "table-unbordered", "col-4"],
                }
            }
        })

    @classmethod
    def _get_observed_value(cls, evr):
        result = evr.result
        if result is None:
            return "--"

        expectation_type = evr.expectation_config["expectation_type"]

        if expectation_type == "expect_column_kl_divergence_to_be_less_than":
            return cls._get_kl_divergence_observed_value(evr)
        elif expectation_type == "expect_column_quantile_values_to_be_between":
            return cls._get_quantile_values_observed_value(evr)

        if result.get("observed_value"):
            observed_value = result.get("observed_value")
            if isinstance(observed_value, (integer_types, float)) and not isinstance(observed_value, bool):
                return num_to_str(observed_value, precision=10, use_locale=True)
            return str(observed_value)
        elif expectation_type == "expect_column_values_to_be_null":
            try:
                notnull_percent = result["unexpected_percent"]
                return num_to_str(100 - notnull_percent, precision=5, use_locale=True) + "% null"
            except KeyError:
                return "unknown % null"
        elif expectation_type == "expect_column_values_to_not_be_null":
            try:
                null_percent = result["unexpected_percent"]
                return num_to_str(100 - null_percent, precision=5, use_locale=True) + "% not null"
            except KeyError:
                return "unknown % not null"
        elif result.get("unexpected_percent") is not None:
            return num_to_str(result.get("unexpected_percent"), precision=5) + "% unexpected"
        else:
            return "--"

    @classmethod
    def _process_content_block(cls, content_block, has_failed_evr):
        super(ValidationResultsTableContentBlockRenderer, cls)._process_content_block(content_block, has_failed_evr)
        content_block.header_row = ["Status", "Expectation", "Observed Value"]

        if has_failed_evr is False:
            styling = deepcopy(content_block.styling) if content_block.styling else {}
            if styling.get("classes"):
                styling["classes"].append("hide-succeeded-validations-column-section-target-child")
            else:
                styling["classes"] = ["hide-succeeded-validations-column-section-target-child"]

            content_block.styling = styling

    @classmethod
    def _get_content_block_fn(cls, expectation_type):
        expectation_string_fn = getattr(cls, expectation_type, None)
        if expectation_string_fn is None:
            expectation_string_fn = getattr(cls, "_missing_content_block_fn")

        #This function wraps expect_* methods from ExpectationStringRenderer to generate table classes
        def row_generator_fn(evr, styling=None, include_column_name=True):
            expectation = evr.expectation_config
            expectation_string_cell = expectation_string_fn(expectation, styling, include_column_name)

            status_cell = [cls._get_status_icon(evr)]
            unexpected_statement = []
            unexpected_table = None
            observed_value = ["--"]

            try:
                unexpected_statement = cls._get_unexpected_statement(evr)
            except Exception as e:
                logger.error("Exception occurred during data docs rendering: ", e, exc_info=True)
            try:
                unexpected_table = cls._get_unexpected_table(evr)
            except Exception as e:
                logger.error("Exception occurred during data docs rendering: ", e, exc_info=True)
            try:
                observed_value = [cls._get_observed_value(evr)]
            except Exception as e:
                logger.error("Exception occurred during data docs rendering: ", e, exc_info=True)

            # If the expectation has some unexpected values...:
            if unexpected_statement:
                expectation_string_cell += unexpected_statement
            if unexpected_table:
                expectation_string_cell.append(unexpected_table)

            if len(expectation_string_cell) > 1:
                return [status_cell + [expectation_string_cell] + observed_value]
            else:
                return [status_cell + expectation_string_cell + observed_value]

        return row_generator_fn
