from django.urls import path

from narraint.frontend.ui.views import get_autocompletion, get_check_query, get_query, post_feedback, \
    post_report, get_provenance, get_document_graph, get_tree_info, get_query_sub_count, post_document_link_clicked, \
    get_query_narrative_documents, get_narrative_documents, get_document_ids_for_entity, get_term_to_entity, \
    get_query_document_ids, post_subgroup_feedback, post_paper_view_log, \
    post_drug_ov_search_log, post_drug_ov_subst_href_log, post_drug_ov_chembl_phase_href_log, \
    get_keywords, get_logs_data, get_new_query, get_keyword_search_request, get_explain_translation, \
    post_drug_suggestion, get_clinical_trial_phases, get_last_db_update, get_data_sources, \
    get_explain_document, get_recommend

urlpatterns = [
    path("query", get_query, name="query"),
    path("new_query", get_new_query, name="new_query"),
    path("query_sub_count", get_query_sub_count, name="query_sub_count"),
    path("autocompletion", get_autocompletion, name="autocompletion"),
    path("check_query", get_check_query, name="check_query"),
    path("term_to_entity", get_term_to_entity, name="term_to_entity"),
    path("feedback", post_feedback, name="feedback"),
    path("suggest_drug", post_drug_suggestion, name="suggest_drug"),
    path("subgroup_feedback", post_subgroup_feedback, name="subgroup_feedback"),
    path("provenance", get_provenance, name="provenance"),
    path("explain_document", get_explain_document, name="explain_document"),
    path("report", post_report, name="report"),
    path("document_graph", get_document_graph, name="document_graph"),
    path("tree_info", get_tree_info, name="tree_info"),
    path("document_clicked", post_document_link_clicked, name="document_clicked"),
    path("query_narrative_documents", get_query_narrative_documents, name="query_narrative_documents"),
    path("narrative_documents", get_narrative_documents, name="narrative_documents"),
    path("document_ids_for_entity", get_document_ids_for_entity, name="document_ids_for_entity"),
    path("query_document_ids", get_query_document_ids, name="query_document_ids"),
    path("paper_view_log", post_paper_view_log, name="paper_view_log"),
    path("drug_search_log", post_drug_ov_search_log, name="drug_search_log"),
    path("drug_substance_forward_log", post_drug_ov_subst_href_log, name="drug_substance_forward_log"),
    path("drug_chembl_phase_log", post_drug_ov_chembl_phase_href_log, name="drug_chembl_phase_log"),
    path("keywords", get_keywords, name="keywords"),
    path("logs_data", get_logs_data, name="logs_data"),
    path("keyword_search_request", get_keyword_search_request, name="keyword_search_request"),
    path("explain_translation", get_explain_translation, name="explain_translation"),
    path("clinical_trial_phases", get_clinical_trial_phases, name="clinical_trial_phases"),
    path("database_update", get_last_db_update, name="database_update"),
    path("document_collections", get_data_sources, name="document_collections"),
    path("recommend", get_recommend, name="recommend"),
]
