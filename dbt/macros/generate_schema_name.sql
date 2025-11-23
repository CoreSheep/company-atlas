{% macro generate_schema_name(custom_schema_name, node) -%}
    {# 
        Custom schema naming: Use only the explicit schema name without any prefix.
        This ensures schemas like 'raw', 'bronze', 'marts' are used as-is,
        not prefixed with target.schema (e.g., 'dev_raw').
    #}
    {%- if custom_schema_name is none -%}
        {# Fallback to target.schema if no custom schema is specified #}
        {{ target.schema | trim | upper }}
    {%- else -%}
        {# Use ONLY the custom schema name, no prefix, no concatenation #}
        {{ custom_schema_name | trim | upper }}
    {%- endif -%}
{%- endmacro %}

