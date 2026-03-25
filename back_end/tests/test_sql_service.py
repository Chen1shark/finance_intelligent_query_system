import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.sql_service import SQLService


class SQLServiceTestCase(unittest.TestCase):
    def test_finalize_sql_expands_single_row_query_to_all_fields(self):
        sql = "SELECT contract_name, remain_days, volume FROM etf_option_data WHERE contract_name LIKE '%购%' ORDER BY volume DESC LIMIT 1;"
        finalized = SQLService.finalize_sql(sql, sql)
        self.assertEqual(
            finalized,
            "SELECT * FROM etf_option_data WHERE contract_name LIKE '%购%' ORDER BY volume DESC LIMIT 1;",
        )

    def test_finalize_sql_keeps_list_query_projection(self):
        sql = "SELECT contract_name, volume FROM etf_option_data WHERE volume > 1000 ORDER BY volume DESC;"
        finalized = SQLService.finalize_sql(sql, sql)
        self.assertEqual(finalized, sql)

    def test_detect_result_mode_returns_detail_only_for_single_row_results(self):
        sql = "SELECT * FROM etf_option_data ORDER BY volume DESC LIMIT 1;"
        rows = [{"contract_code": "100000"}]
        self.assertEqual(SQLService.detect_result_mode(sql, rows), "detail")
        self.assertEqual(SQLService.detect_result_mode(sql, []), "list")


if __name__ == "__main__":
    unittest.main()
