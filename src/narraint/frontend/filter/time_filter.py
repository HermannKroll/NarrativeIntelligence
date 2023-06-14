from narraint.queryengine.result import QueryDocumentResult


class TimeFilter:

    @staticmethod
    def filter_documents_by_year(results: [QueryDocumentResult], year_start: int, year_end: int):
        if year_start and year_end:
            return list([r for r in results if year_start <= r.publication_year <= year_end])
        elif year_start:
            return list([r for r in results if year_start <= r.publication_year])
        elif year_end:
            return list([r for r in results if r.publication_year <= year_end])
        else:
            return results

    @staticmethod
    def aggregate_years(results: [QueryDocumentResult]):
        # Output: {1992: 10, 1993: 100, ... }
        year_aggregation = {}
        for r in results:
            current_year = r.publication_year
            if current_year > 0:
                if current_year in year_aggregation:
                    year_aggregation.update({current_year: year_aggregation[current_year] + 1})
                else:
                    year_aggregation.update({current_year: 1})
        found_years = list(year_aggregation.keys())
        found_years.sort()
        try:
            all_years = list(range(found_years[0], found_years[-1] + 1))
        except:
            all_years = found_years
        for year in set(all_years) - set(found_years) & set(all_years):
            year_aggregation.update({year: 0})
        return year_aggregation
