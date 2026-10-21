# Tableau parameter lists

Generated from `data/marts/dim_nodes.csv`. In the parameter dialog choose **List**, then **Paste from Clipboard**:
copy a block below (value, tab, display text) and Tableau fills both the Value and the Display As columns.

## p_selected_exposure (27 values, grouped like the prototype's dropdown)

```
exposure.acme_core.board_kpi_pack	Board KPI Pack
exposure.acme_core.customer_360	Customer 360
exposure.acme_core.daily_sales_snapshot	Daily Sales Snapshot
exposure.acme_core.executive_revenue_dashboard	Executive Revenue Dashboard
exposure.acme_core.finance_close_tracker	Finance Close Tracker
exposure.acme_core.inventory_health	Inventory Health
exposure.acme_core.lineage_control_tower	Lineage Control Tower
exposure.acme_marketing.marketing_campaign_performance	Marketing Campaign Performance
exposure.acme_product.product_engagement	Product Engagement
exposure.acme_core.q3_sales_summary_ai	Q3 Sales Summary (AI)
exposure.acme_core.revenue_dashboard_copy	Revenue Dashboard (copy)
exposure.acme_core.revenue_overview_ai	Revenue Overview (AI)
exposure.acme_core.revenue_by_channel_v2	Revenue by Channel v2
exposure.acme_marketing.sales_pipeline	Sales Pipeline
exposure.acme_core.supply_chain_ops	Supply Chain Ops
exposure.acme_product.support_sla_tracker	Support SLA Tracker
exposure.acme_product.web_funnel_analysis	Web Funnel Analysis
exposure.acme_product.churn_prediction_model	Churn Prediction Model
exposure.acme_product.demand_forecast_app	Demand Forecast App
exposure.acme_core.partner_revenue_share	Partner Revenue Share
exposure.acme_product.pricing_experiment_analysis	Pricing Experiment Analysis
exposure.acme_core.finance_qa_agent	Finance Q&A Agent
exposure.acme_core.merchandising_copilot	Merchandising Copilot
exposure.acme_core.store_ops_hub	Store Ops Hub
exposure.observed.undeclared_regional_hub	Unregistered: personal Claude hub
exposure.observed.undeclared_pricing_agent	Unregistered: pricing agent
exposure.observed.undeclared_promo_notebook	Unregistered: scheduled notebook
```

## p_selected_node (121 values, sources to semantic layer, layer prefix in the display text)

```
source.acme_core.raw_dbt_artifacts.run_results	Sources · raw_dbt_artifacts.run_results
source.acme_product.raw_events.app_events	Sources · raw_events.app_events
source.acme_product.raw_events.page_views	Sources · raw_events.page_views
source.acme_product.raw_events.search_events	Sources · raw_events.search_events
source.acme_product.raw_events.web_sessions	Sources · raw_events.web_sessions
source.acme_product.raw_experiments.assignments	Sources · raw_experiments.assignments
source.acme_marketing.raw_google_ads.ad_stats	Sources · raw_google_ads.ad_stats
source.acme_marketing.raw_google_ads.campaigns	Sources · raw_google_ads.campaigns
source.acme_marketing.raw_hubspot.companies	Sources · raw_hubspot.companies
source.acme_marketing.raw_hubspot.contacts	Sources · raw_hubspot.contacts
source.acme_marketing.raw_hubspot.deals	Sources · raw_hubspot.deals
source.acme_marketing.raw_meta_ads.ad_insights	Sources · raw_meta_ads.ad_insights
source.acme_core.raw_netsuite.accounts	Sources · raw_netsuite.accounts
source.acme_core.raw_netsuite.gl_entries	Sources · raw_netsuite.gl_entries
source.acme_core.raw_netsuite.journal_lines	Sources · raw_netsuite.journal_lines
source.acme_core.raw_pos.store_sales	Sources · raw_pos.store_sales
source.acme_core.raw_shopify.customers	Sources · raw_shopify.customers
source.acme_core.raw_shopify.order_items	Sources · raw_shopify.order_items
source.acme_core.raw_shopify.orders	Sources · raw_shopify.orders
source.acme_core.raw_shopify.products	Sources · raw_shopify.products
source.acme_core.raw_stripe.payments	Sources · raw_stripe.payments
source.acme_core.raw_stripe.refunds	Sources · raw_stripe.refunds
source.acme_core.raw_wms.inventory	Sources · raw_wms.inventory
source.acme_core.raw_wms.shipments	Sources · raw_wms.shipments
source.acme_core.raw_wms.warehouses	Sources · raw_wms.warehouses
source.acme_product.raw_zendesk.ticket_comments	Sources · raw_zendesk.ticket_comments
source.acme_product.raw_zendesk.tickets	Sources · raw_zendesk.tickets
model.acme_core.stg_dbt__run_results	Staging · stg_dbt__run_results
model.acme_product.stg_events__app_events	Staging · stg_events__app_events
model.acme_product.stg_events__app_installs	Staging · stg_events__app_installs
model.acme_product.stg_events__page_views	Staging · stg_events__page_views
model.acme_product.stg_events__search_events	Staging · stg_events__search_events
model.acme_product.stg_events__web_sessions	Staging · stg_events__web_sessions
model.acme_product.stg_experiments__assignments	Staging · stg_experiments__assignments
model.acme_marketing.stg_google_ads__ad_stats	Staging · stg_google_ads__ad_stats
model.acme_marketing.stg_google_ads__campaigns	Staging · stg_google_ads__campaigns
model.acme_marketing.stg_hubspot__companies	Staging · stg_hubspot__companies
model.acme_marketing.stg_hubspot__contacts	Staging · stg_hubspot__contacts
model.acme_marketing.stg_hubspot__deal_stages	Staging · stg_hubspot__deal_stages
model.acme_marketing.stg_hubspot__deals	Staging · stg_hubspot__deals
model.acme_marketing.stg_meta_ads__ad_insights	Staging · stg_meta_ads__ad_insights
model.acme_core.stg_netsuite__accounts	Staging · stg_netsuite__accounts
model.acme_core.stg_netsuite__gl_entries	Staging · stg_netsuite__gl_entries
model.acme_core.stg_netsuite__journal_lines	Staging · stg_netsuite__journal_lines
model.acme_core.stg_pos__store_sales	Staging · stg_pos__store_sales
model.acme_core.stg_shopify__customers	Staging · stg_shopify__customers
model.acme_core.stg_shopify__order_discounts	Staging · stg_shopify__order_discounts
model.acme_core.stg_shopify__order_items	Staging · stg_shopify__order_items
model.acme_core.stg_shopify__orders	Staging · stg_shopify__orders
model.acme_core.stg_shopify__products	Staging · stg_shopify__products
model.acme_core.stg_stripe__payments	Staging · stg_stripe__payments
model.acme_core.stg_stripe__refunds	Staging · stg_stripe__refunds
model.acme_core.stg_wms__inventory	Staging · stg_wms__inventory
model.acme_core.stg_wms__shipments	Staging · stg_wms__shipments
model.acme_core.stg_wms__warehouses	Staging · stg_wms__warehouses
model.acme_product.stg_zendesk__ticket_comments	Staging · stg_zendesk__ticket_comments
model.acme_product.stg_zendesk__tickets	Staging · stg_zendesk__tickets
model.acme_marketing.int_ads__attribution	Intermediate · int_ads__attribution
model.acme_marketing.int_ads__unified	Intermediate · int_ads__unified
model.acme_product.int_app__engagement	Intermediate · int_app__engagement
model.acme_marketing.int_campaigns__spend_daily	Intermediate · int_campaigns__spend_daily
model.acme_marketing.int_contacts__lifecycle	Intermediate · int_contacts__lifecycle
model.acme_product.int_customer_behavior	Intermediate · int_customer_behavior
model.acme_core.int_customers__deduped	Intermediate · int_customers__deduped
model.acme_marketing.int_deals__pipeline	Intermediate · int_deals__pipeline
model.acme_product.int_experiments__assignments_enriched	Intermediate · int_experiments__assignments_enriched
model.acme_product.int_funnel__steps	Intermediate · int_funnel__steps
model.acme_core.int_gl__mapped	Intermediate · int_gl__mapped
model.acme_core.int_inventory__snapshots	Intermediate · int_inventory__snapshots
model.acme_core.int_orders__enriched	Intermediate · int_orders__enriched
model.acme_core.int_payments__reconciled	Intermediate · int_payments__reconciled
model.acme_core.int_products__catalog	Intermediate · int_products__catalog
model.acme_core.int_revenue__daily	Intermediate · int_revenue__daily
model.acme_product.int_sessions__stitched	Intermediate · int_sessions__stitched
model.acme_core.int_shipments__sla	Intermediate · int_shipments__sla
model.acme_core.int_store_sales__daily	Intermediate · int_store_sales__daily
model.acme_product.int_tickets__lifecycle	Intermediate · int_tickets__lifecycle
model.acme_marketing.dim_companies	Marts · dim_companies
model.acme_marketing.dim_contacts	Marts · dim_contacts
model.acme_core.dim_customer_360	Marts · dim_customer_360
model.acme_product.dim_customer_behavior	Marts · dim_customer_behavior
model.acme_core.dim_customers	Marts · dim_customers
model.acme_core.dim_products	Marts · dim_products
model.acme_core.dim_stores	Marts · dim_stores
model.acme_marketing.fct_ad_spend_daily	Marts · fct_ad_spend_daily
model.acme_product.fct_app_engagement	Marts · fct_app_engagement
model.acme_marketing.fct_attribution	Marts · fct_attribution
model.acme_core.fct_board_kpis	Marts · fct_board_kpis
model.acme_marketing.fct_campaign_performance	Marts · fct_campaign_performance
model.acme_product.fct_churn_features	Marts · fct_churn_features
model.acme_product.fct_demand_signals	Marts · fct_demand_signals
model.acme_product.fct_experiment_results	Marts · fct_experiment_results
model.acme_core.fct_finance_close	Marts · fct_finance_close
model.acme_product.fct_funnel_daily	Marts · fct_funnel_daily
model.acme_core.fct_gl_journal	Marts · fct_gl_journal
model.acme_core.fct_inventory_daily	Marts · fct_inventory_daily
model.acme_marketing.fct_marketing_roi	Marts · fct_marketing_roi
model.acme_core.fct_ops_model_health	Marts · fct_ops_model_health
model.acme_core.fct_order_items	Marts · fct_order_items
model.acme_core.fct_orders	Marts · fct_orders
model.acme_core.fct_partner_payouts	Marts · fct_partner_payouts
model.acme_core.fct_payments	Marts · fct_payments
model.acme_marketing.fct_pipeline	Marts · fct_pipeline
model.acme_core.fct_revenue_daily	Marts · fct_revenue_daily
model.acme_product.fct_sessions	Marts · fct_sessions
model.acme_core.fct_shipments	Marts · fct_shipments
model.acme_core.fct_store_sales	Marts · fct_store_sales
model.acme_product.fct_support_sla_daily	Marts · fct_support_sla_daily
model.acme_product.fct_tickets	Marts · fct_tickets
semantic.power_bi.pbi_inventory	BI semantic layer · pbi_inventory
semantic.power_bi.pbi_marketing	BI semantic layer · pbi_marketing
semantic.power_bi.pbi_support	BI semantic layer · pbi_support
semantic.tableau.pds_board_kpis	BI semantic layer · pds_board_kpis
semantic.tableau.pds_commerce_sales	BI semantic layer · pds_commerce_sales
semantic.tableau.pds_finance_close	BI semantic layer · pds_finance_close
semantic.tableau.pds_finance_revenue	BI semantic layer · pds_finance_revenue
semantic.tableau.pds_ops_monitor	BI semantic layer · pds_ops_monitor
semantic.tableau.pds_sales_pipeline	BI semantic layer · pds_sales_pipeline
semantic.tableau.pds_web_funnel	BI semantic layer · pds_web_funnel
semantic.sigma.sigma_customer_360	BI semantic layer · sigma_customer_360
semantic.sigma.sigma_product_engagement	BI semantic layer · sigma_product_engagement
```

## p_selected_node_key

Integer, **All** values (it is only ever set by actions). Default 35 = `stg_netsuite__journal_lines`.
