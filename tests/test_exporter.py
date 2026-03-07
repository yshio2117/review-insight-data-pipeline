import pytest
import os
from unittest.mock import patch, MagicMock
from src.reason_extraction.output.exporter import load_reason_records_to_bigquery


def test_load_reason_records_to_bigquery():
    """Test that the function load_reason_records_to_bigquery is executed with correct data and table name"""
   

    dummy_records = [
        {
            "sentiment_type": "negative",
            "subject": ["部屋"],
            "predicate": "汚い",
            "confidence": 0.9,
            "review_id": "rev_123",
            "reason_id": "reas_abc",
            "run_id": "run_999"
        }
    ]

    # set environment variables
    env_vars = {
        "PROJECT_ID": "test_project",
        "DATASET_ID": "test_dataset"
    }

    # set BigQuery Mock and patch environment variables
    with patch.dict(os.environ, env_vars), \
         patch("src.reason_extraction.output.exporter.bigquery.Client") as MockClient, \
         patch("src.reason_extraction.output.exporter.bigquery.LoadJobConfig"):
        
        # mock Client and LoadJobConfig to prevent actual BigQuery calls during the test
        mock_client_instance = MockClient.return_value
        mock_load_job = MagicMock()
        mock_client_instance.load_table_from_json.return_value = mock_load_job
        
        
        load_reason_records_to_bigquery(dummy_records)

        
        # check if the client was called once
        MockClient.assert_called_once()
        
        expected_table = "test_project.test_dataset.review_reasons"
        
        # check if load_table_from_json was called with the correct arguments
        mock_client_instance.load_table_from_json.assert_called_once()
        args, kwargs = mock_client_instance.load_table_from_json.call_args
        
        assert args[0] == dummy_records
        assert args[1] == expected_table
        assert "job_config" in kwargs    # check if job_config is passed as a keyword argument
        
        # check if result() was called to wait for the job completion
        mock_load_job.result.assert_called_once()