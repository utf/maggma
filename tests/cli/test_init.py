import pytest
from click.testing import CliRunner
from maggma.cli import run
from maggma.stores import MongoStore, MemoryStore
from maggma.builders import CopyBuilder
from monty.serialization import dumpfn
from datetime import datetime


@pytest.fixture
def mongostore():
    store = MongoStore("maggma_test", "test")
    store.connect()
    store.remove_docs({})
    yield store
    store.remove_docs({})
    store._collection.drop()


@pytest.fixture
def reporting_store():
    store = MongoStore("maggma_test", "reporting")
    store.connect()
    store.remove_docs({})
    yield store
    store.remove_docs({})
    store._collection.drop()


def test_basic_run():

    runner = CliRunner()
    result = runner.invoke(run, ["--help"])
    assert result.exit_code == 0

    result = runner.invoke(run)
    assert result.exit_code == 0


def test_run_builder(mongostore):

    memorystore = MemoryStore("temp")
    builder = CopyBuilder(mongostore, memorystore)

    mongostore.update(
        [
            {mongostore.key: i, mongostore.last_updated_field: datetime.utcnow()}
            for i in range(10)
        ]
    )

    runner = CliRunner()
    with runner.isolated_filesystem():
        dumpfn(builder, "test_builder.json")
        result = runner.invoke(run, ["-v", "test_builder.json"])
        assert result.exit_code == 0
        assert "CopyBuilder" in result.output
        assert "SerialProcessor" in result.output

        result = runner.invoke(run, ["-v", "-n", "2", "test_builder.json"])
        assert result.exit_code == 0
        assert "CopyBuilder" in result.output
        assert "MultiProcessor" in result.output


def test_reporting(mongostore, reporting_store):

    memorystore = MemoryStore("temp")
    builder = CopyBuilder(mongostore, memorystore)

    mongostore.update(
        [
            {mongostore.key: i, mongostore.last_updated_field: datetime.utcnow()}
            for i in range(10)
        ]
    )

    runner = CliRunner()
    with runner.isolated_filesystem():
        dumpfn(builder, "test_builder.json")
        dumpfn(reporting_store, "test_reporting_store.json")
        result = runner.invoke(
            run, ["-v", "test_builder.json", "-r", "test_reporting_store.json"]
        )
        assert result.exit_code == 0

        report_docs = list(reporting_store.query())
        assert len(report_docs) == 3

        start_doc = next(d for d in report_docs if d["event"] == "BUILD_STARTED")
        assert "sources" in start_doc
        assert "targets" in start_doc

        end_doc = next(d for d in report_docs if d["event"] == "BUILD_ENDED")
        assert "errors" in end_doc
        assert "warnings" in end_doc

        update_doc = next(d for d in report_docs if d["event"] == "UPDATE")
        assert "items" in update_doc
