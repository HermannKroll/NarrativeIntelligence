from unittest import TestCase

from narraint.frontend.filter.classification_filter import ClassificationFilter
from narraint.frontend.filter.time_filter import TimeFilter
from narraint.frontend.filter.title_filter import TitleFilter
from narraint.queryengine.result import QueryDocumentResult


class FilterTestCase(TestCase):

    def setUp(self) -> None:
        self.results = [
            QueryDocumentResult(1, "This is a test", "", "", 2020, 10, {}, 0, {}, "", document_classes=["a"]),
            QueryDocumentResult(2, "This is a small test", "", "", 2021, 10, {}, 0, {}, ""),
            QueryDocumentResult(3, "Lets test this", "", "", 2022, 10, {}, 0, {}, "", document_classes=["c"]),
            QueryDocumentResult(4, "Not a", "", "", 2023, 10, {}, 0, {}, ""),
            QueryDocumentResult(5, "Hello", "", "", 2024, 10, {}, 0, {}, "", document_classes=["a", "b"])]

    def test_title_filter(self):
        self.assertEqual(3, len(TitleFilter.filter_documents(self.results, "Test")))
        self.assertEqual(3, len(TitleFilter.filter_documents(self.results, "TesT")))
        self.assertEqual(3, len(TitleFilter.filter_documents(self.results, "test")))
        self.assertEqual(3, len(TitleFilter.filter_documents(self.results, "te*")))
        self.assertEqual(3, len(TitleFilter.filter_documents(self.results, "*es*")))
        self.assertEqual(4, len(TitleFilter.filter_documents(self.results, "*e*")))
        self.assertEqual(2, len(TitleFilter.filter_documents(self.results, "test and a")))
        self.assertEqual(4, len(TitleFilter.filter_documents(self.results, "test or a")))
        self.assertEqual(5, len(TitleFilter.filter_documents(self.results, "(test or a) or hello")))
        self.assertEqual(0, len(TitleFilter.filter_documents(self.results, "(test or a) and hello")))

        dsys = QueryDocumentResult(5, "This is a syStematic about review  bla", "", "", 2024, 10, {}, 0, {}, "")
        self.assertEqual(1, len(TitleFilter.filter_documents([dsys], "systemat")))
        self.assertEqual(1, len(TitleFilter.filter_documents([dsys], "systematIC")))
        self.assertEqual(1, len(TitleFilter.filter_documents([dsys], "systemat review")))
        self.assertEqual(1, len(TitleFilter.filter_documents([dsys], "systemat* review")))
        self.assertEqual(1, len(TitleFilter.filter_documents([dsys], "systemat* revi*")))
        self.assertEqual(1, len(TitleFilter.filter_documents([dsys], "systematic review")))
        self.assertEqual(0, len(TitleFilter.filter_documents([dsys], "systematic+review")))
        self.assertEqual(1, len(TitleFilter.filter_documents([dsys], "systemat or review")))
        self.assertEqual(1, len(TitleFilter.filter_documents([dsys], "systemat and review")))

    def test_time_filter(self):
        self.assertEqual(5, len(TimeFilter.filter_documents_by_year(self.results, year_start=2018, year_end=0)))
        self.assertEqual(5, len(TimeFilter.filter_documents_by_year(self.results, year_start=2019, year_end=0)))
        self.assertEqual(5, len(TimeFilter.filter_documents_by_year(self.results, year_start=2018, year_end=2025)))
        self.assertEqual(3, len(TimeFilter.filter_documents_by_year(self.results, year_start=2018, year_end=2022)))
        self.assertEqual(5, len(TimeFilter.filter_documents_by_year(self.results, year_start=0, year_end=2025)))
        self.assertEqual(2, len(TimeFilter.filter_documents_by_year(self.results, year_start=2023, year_end=2025)))

    def test_classification_filter(self):
        self.assertEqual(2, len(ClassificationFilter.filter_documents(self.results, document_classes=["a"])))
        self.assertEqual(1, len(ClassificationFilter.filter_documents(self.results, document_classes=["b"])))
        self.assertEqual(1, len(ClassificationFilter.filter_documents(self.results, document_classes=["c"])))
        self.assertEqual(0, len(ClassificationFilter.filter_documents(self.results, document_classes=["d"])))
        self.assertEqual(5, len(ClassificationFilter.filter_documents(self.results, document_classes=None)))
