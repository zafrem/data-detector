"""Command-line interface for data-detector."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, List, Optional, Tuple

import click
import yaml

from datadetector import __version__
from datadetector.adapters import get_adapter_class
from datadetector.data_explorer import DataExplorer
from datadetector.data_inventory import DataInventoryGenerator
from datadetector.data_lineage import DataLineageTracer
from datadetector.engine import Engine
from datadetector.mlops import (
    GateReport,
    scan_rag_records,
    scan_text,
    scan_training_data,
)
from datadetector.models import PrivyscopeConfig, RedactionStrategy, TransformerConfig
from datadetector.registry import load_registry
from datadetector.resource_models import (
    ConnectionConfig,
    DataResource,
    InventoryFormat,
    ResourceScanResult,
    ResourceType,
    ScanStrategy,
)
from datadetector.utils.serialization import from_dict, to_dict


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def _privyscope_config(ner: bool, ner_lang: Optional[str]) -> Optional[PrivyscopeConfig]:
    """Build a PrivyscopeConfig from the shared --ner/--ner-lang flags (None if off)."""
    if not ner:
        return None
    return PrivyscopeConfig(enabled=True, lang=ner_lang)


@click.group()
@click.version_option(version=__version__)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """data-detector: Detect and mask personal information."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose)


@main.command()
@click.option(
    "--text",
    "-t",
    help="Text to search (use --file for file input)",
)
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    help="File to search",
)
@click.option(
    "--ns",
    "--namespace",
    "namespaces",
    multiple=True,
    help="Namespaces to search (can be used multiple times)",
)
@click.option(
    "--patterns",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Pattern files to load (uses defaults if not specified)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
@click.option(
    "--include-text",
    is_flag=True,
    help="Include matched text in output (respects privacy policy)",
)
@click.option(
    "--first-only",
    is_flag=True,
    help="Stop after finding first match (faster, useful for detection checks)",
)
@click.option(
    "--on-match",
    type=click.Choice(["exit", "skip"]),
    default="skip",
    help="Action when matches found: 'exit' (fail/non-zero code) or 'skip' (pass/zero code)",
)
@click.option(
    "--ml-context",
    is_flag=True,
    help="Enable ML-based context classification (improves precision)",
)
@click.option(
    "--ner",
    is_flag=True,
    help="Enable NER detection via the privyscope backend (pii-engine submodule), "
    "to catch entities regex misses. Needs `pip install -e pii-engine`.",
)
@click.option(
    "--ner-lang",
    default=None,
    help="Language for --ner (e.g. 'ko', 'en'). Omit to use the sole installed "
    "language pack.",
)
@click.pass_context
def find(
    ctx: click.Context,
    text: Optional[str],
    file: Optional[Path],
    namespaces: Tuple[str, ...],
    patterns: Tuple[Path, ...],
    output: str,
    include_text: bool,
    first_only: bool,
    on_match: str,
    ml_context: bool,
    ner: bool,
    ner_lang: Optional[str],
) -> None:
    """Find PII in text or file."""
    # Load text
    if text is None and file is None:
        click.echo("Error: Must provide --text or --file", err=True)
        sys.exit(1)

    if file:
        text = file.read_text(encoding="utf-8")
    assert text is not None

    # Load patterns
    pattern_paths = [str(p) for p in patterns] if patterns else None
    registry = load_registry(paths=pattern_paths)

    # Configure Transformer context classification (--ml-context).
    transformer_config = None
    if ml_context:
        transformer_config = TransformerConfig(enable_context_classifier=True)

    # Create engine and find. --ner drives the privyscope NER backend
    # (pii-engine), which occupies the engine's NER slot.
    engine = Engine(
        registry,
        transformer_config=transformer_config,
        privyscope_config=_privyscope_config(ner, ner_lang),
    )
    ns_list = list(namespaces) if namespaces else None
    result = engine.find(
        text, namespaces=ns_list, include_matched_text=include_text, stop_on_first_match=first_only
    )

    # Output results
    if output == "json":
        matches_data = [
            {
                "ns_id": m.ns_id,
                "namespace": m.namespace,
                "pattern_id": m.pattern_id,
                "category": m.category.value,
                "start": m.start,
                "end": m.end,
                "matched_text": m.matched_text,
                "severity": m.severity.value,
                "score": m.score,
            }
            for m in result.matches
        ]
        click.echo(
            json.dumps(
                {
                    "match_count": result.match_count,
                    "namespaces_searched": result.namespaces_searched,
                    "matches": matches_data,
                },
                indent=2,
            )
        )
    else:
        click.echo(f"Found {result.match_count} matches")
        for match in result.matches:
            text_preview = f" [{match.matched_text}]" if match.matched_text else ""
            click.echo(
                f"  {match.ns_id} ({match.category.value}) at {match.start}-{match.end}"
                f" [severity: {match.severity.value}] [score: {match.score:.2f}]{text_preview}"
            )
            if match.context_evidence:
                for evidence in match.context_evidence:
                    click.echo(f"    - {evidence}")

    # Handle exit mode
    if result.match_count > 0 and on_match == "exit":
        sys.exit(1)


@main.command()
@click.option(
    "--text",
    "-t",
    required=True,
    help="Text to validate",
)
@click.option(
    "--ns-id",
    required=True,
    help="Pattern namespace/id (e.g., kr/mobile)",
)
@click.option(
    "--patterns",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Pattern files to load",
)
@click.pass_context
def validate(
    ctx: click.Context,
    text: str,
    ns_id: str,
    patterns: Tuple[Path, ...],
) -> None:
    """Validate text against a specific pattern."""
    # Load patterns
    pattern_paths = [str(p) for p in patterns] if patterns else None
    registry = load_registry(paths=pattern_paths)

    # Create engine and validate
    engine = Engine(registry)

    try:
        result = engine.validate(text, ns_id)
        if result.is_valid:
            click.echo(f"✓ Valid {ns_id}")
            sys.exit(0)
        else:
            click.echo(f"✗ Invalid {ns_id}")
            sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(2)


@main.command()
@click.option(
    "--text",
    "-t",
    help="Text to redact (use --in for file input)",
)
@click.option(
    "--in",
    "input_file",
    type=click.Path(exists=True, path_type=Path),
    help="Input file to redact",
)
@click.option(
    "--out",
    "output_file",
    type=click.Path(path_type=Path),
    help="Output file (prints to stdout if not specified)",
)
@click.option(
    "--ns",
    "--namespace",
    "namespaces",
    multiple=True,
    help="Namespaces to search",
)
@click.option(
    "--patterns",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Pattern files to load",
)
@click.option(
    "--strategy",
    type=click.Choice(["mask", "hash", "tokenize"]),
    default="mask",
    help="Redaction strategy",
)
@click.option(
    "--stats",
    is_flag=True,
    help="Print redaction statistics",
)
@click.option(
    "--ner",
    is_flag=True,
    help="Enable NER detection via the privyscope backend (pii-engine submodule), "
    "to catch entities regex misses. Needs `pip install -e pii-engine`.",
)
@click.option(
    "--ner-lang",
    default=None,
    help="Language for --ner (e.g. 'ko', 'en'). Omit to use the sole installed "
    "language pack.",
)
@click.pass_context
def redact(
    ctx: click.Context,
    text: Optional[str],
    input_file: Optional[Path],
    output_file: Optional[Path],
    namespaces: Tuple[str, ...],
    patterns: Tuple[Path, ...],
    strategy: str,
    stats: bool,
    ner: bool,
    ner_lang: Optional[str],
) -> None:
    """Redact PII from text or file."""
    # Load text
    if text is None and input_file is None:
        click.echo("Error: Must provide --text or --in", err=True)
        sys.exit(1)

    if input_file:
        text = input_file.read_text(encoding="utf-8")
    assert text is not None

    # Load patterns
    pattern_paths = [str(p) for p in patterns] if patterns else None
    registry = load_registry(paths=pattern_paths)

    # Create engine and redact
    engine = Engine(registry, privyscope_config=_privyscope_config(ner, ner_lang))
    ns_list = list(namespaces) if namespaces else None
    redaction_strategy = RedactionStrategy(strategy)
    result = engine.redact(text, namespaces=ns_list, strategy=redaction_strategy)

    # Output redacted text
    if output_file:
        output_file.write_text(result.redacted_text, encoding="utf-8")
        if stats:
            click.echo(f"Redacted {result.redaction_count} items to {output_file}")
    else:
        click.echo(result.redacted_text)
        if stats:
            click.echo(f"\n[Redacted {result.redaction_count} items]", err=True)


@main.command()
@click.option(
    "--port",
    "-p",
    type=int,
    default=8080,
    help="Port to listen on",
)
@click.option(
    "--host",
    "-h",
    default="0.0.0.0",
    help="Host to bind to",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file",
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload (development only)",
)
@click.pass_context
def serve(
    ctx: click.Context,
    port: int,
    host: str,
    config: Optional[Path],
    reload: bool,
) -> None:
    """Start HTTP/gRPC server."""
    try:
        import uvicorn

        from datadetector.server import create_app
    except ImportError:
        click.echo(
            "Error: Server dependencies not installed. "
            "Install with: pip install data-detector[server]",
            err=True,
        )
        sys.exit(1)

    # Load config
    config_data = {}
    if config:
        with open(config) as f:
            config_data = yaml.safe_load(f)

    # Override with CLI options
    server_config = config_data.get("server", {})
    port = port or server_config.get("port", 8080)
    host = host or server_config.get("host", "0.0.0.0")

    click.echo(f"Starting server on {host}:{port}")

    # Create app
    app = create_app(config_data)

    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level="info" if ctx.obj.get("verbose") else "warning",
    )


@main.command()
@click.option(
    "--patterns",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    multiple=True,
    help="Pattern files to list",
)
def list_patterns(patterns: Tuple[Path, ...]) -> None:
    """List available patterns."""
    pattern_paths = [str(p) for p in patterns] if patterns else None
    registry = load_registry(paths=pattern_paths)

    click.echo(f"Loaded {len(registry)} patterns from {len(registry.namespaces)} namespaces\n")

    for namespace in sorted(registry.namespaces.keys()):
        click.echo(f"Namespace: {namespace}")
        for pattern in registry.get_namespace_patterns(namespace):
            click.echo(f"  {pattern.id:<20} {pattern.category.value:<15} {pattern.description}")
        click.echo()


@main.group()
@click.pass_context
def resource(ctx: click.Context) -> None:
    """Scan data resources (databases, Kafka, APIs, files) and manage inventories."""
    pass


@resource.command()
@click.option(
    "--type",
    "-t",
    "resource_type",
    required=True,
    type=click.Choice(["database", "kafka", "api", "file_storage", "vector_db", "training_data"]),
    help="Resource type",
)
@click.option("--uri", "-u", required=True, help="Connection URI (e.g., sqlite:///data.db)")
@click.option("--name", "-n", default="cli-scan", help="Resource name")
@click.option(
    "--strategy",
    "-s",
    type=click.Choice(["metadata_only", "sample", "full"]),
    default="sample",
    help="Scan strategy",
)
@click.option("--limit", "-l", type=int, default=100, help="Sample limit per field")
@click.option(
    "--ns",
    "namespaces",
    multiple=True,
    help="Namespaces to search",
)
@click.option(
    "--out",
    "-o",
    type=click.Path(path_type=Path),
    help="Output scan result JSON file",
)
@click.option(
    "--ner",
    is_flag=True,
    help="Enable NER detection via the privyscope backend (pii-engine submodule), "
    "to catch entities regex misses. Needs `pip install -e pii-engine`.",
)
@click.option(
    "--ner-lang",
    default=None,
    help="Language for --ner (e.g. 'ko', 'en'). Omit to use the sole installed "
    "language pack.",
)
@click.pass_context
def scan(
    ctx: click.Context,
    resource_type: str,
    uri: str,
    name: str,
    strategy: str,
    limit: int,
    namespaces: Tuple[str, ...],
    out: Optional[Path],
    ner: bool,
    ner_lang: Optional[str],
) -> None:
    """Scan a data resource for PII."""
    registry = load_registry()
    engine = Engine(registry, privyscope_config=_privyscope_config(ner, ner_lang))
    explorer = DataExplorer(engine, sample_limit=limit, namespaces=list(namespaces))

    resource = DataResource(
        name=name,
        resource_type=ResourceType(resource_type),
        connection=ConnectionConfig(uri=uri),
    )

    try:
        adapter_cls = get_adapter_class(resource.resource_type)
        with adapter_cls(resource) as adapter:
            click.echo(f"Scanning {resource_type} resource '{name}'...")
            result = explorer.scan(adapter, strategy=ScanStrategy(strategy))

        if result.status.value == "completed":
            click.echo(f"✓ Scan completed: {result.pii_fields} PII fields found.")
        else:
            click.echo(f"✗ Scan failed: {', '.join(result.errors)}")

        if out:
            out.write_text(json.dumps(to_dict(result), indent=2), encoding="utf-8")
            click.echo(f"Scan result saved to {out}")
        else:
            # Print summary if no output file
            click.echo("\nPII Summary:")
            for cr in result.container_results:
                if cr.has_pii:
                    click.echo(f"  Container: {cr.container.name}")
                    for fr in cr.field_results:
                        if fr.pii_detected:
                            cats = ", ".join(c.value for c in fr.categories)
                            click.echo(f"    - {fr.field_info.name}: {cats}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@resource.command()
@click.option(
    "--in",
    "-i",
    "input_files",
    multiple=True,
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Input scan result JSON files",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "csv", "yaml", "html"]),
    default="html",
    help="Output format (default: html)",
)
@click.option(
    "--out",
    "-o",
    type=click.Path(path_type=Path),
    help="Output report file (prints to stdout if not specified)",
)
@click.pass_context
def inventory(
    ctx: click.Context,
    input_files: Tuple[Path, ...],
    format: str,
    out: Optional[Path],
) -> None:
    """Generate a PII inventory report from scan results."""
    gen = DataInventoryGenerator()

    for file_path in input_files:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            scan_result = from_dict(data, ResourceScanResult)
            gen.add_scan_result(scan_result)
        except Exception as e:
            click.echo(f"Error loading {file_path}: {e}", err=True)
            continue

    inventory = gen.generate()
    fmt = InventoryFormat(format)
    result_text = gen.export(inventory, fmt)

    if out:
        out.write_text(result_text, encoding="utf-8")
        click.echo(f"PII Inventory report saved to {out}")
    else:
        click.echo(result_text)


@resource.command()
@click.option(
    "--in",
    "-i",
    "input_files",
    multiple=True,
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Input inventory JSON files (combine inventories from different sources)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["mermaid", "json"]),
    default="mermaid",
    help="Output format (default: mermaid)",
)
@click.option(
    "--link",
    "links",
    multiple=True,
    help="Explicit cross-resource link: 'srcRes:container.field=tgtRes:container.field'",
)
@click.option(
    "--out",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file (prints to stdout if not specified)",
)
@click.pass_context
def lineage(
    ctx: click.Context,
    input_files: Tuple[Path, ...],
    format: str,
    links: Tuple[str, ...],
    out: Optional[Path],
) -> None:
    """Build a PII lineage graph by combining inventory artifacts."""
    tracer = DataLineageTracer()

    loaded = 0
    for file_path in input_files:
        try:
            inventory = DataInventoryGenerator.load_json_str(file_path.read_text(encoding="utf-8"))
            tracer.add_inventory(inventory)
            loaded += 1
        except Exception as e:
            click.echo(f"Error loading {file_path}: {e}", err=True)

    if loaded == 0:
        click.echo("Error: no inventories could be loaded", err=True)
        sys.exit(1)

    for link in links:
        try:
            src, tgt = link.split("=", 1)
            src_res, src_field = src.split(":", 1)
            tgt_res, tgt_field = tgt.split(":", 1)
            tracer.add_cross_resource_link(
                src_res.strip(), src_field.strip(), tgt_res.strip(), tgt_field.strip()
            )
        except ValueError:
            click.echo(
                f"Warning: ignoring malformed --link '{link}' "
                "(expected 'srcRes:container.field=tgtRes:container.field')",
                err=True,
            )

    tracer.build_graph()

    if format == "mermaid":
        output = tracer.to_mermaid()
    else:
        data = tracer.to_dict()
        data["pii_flow_summary"] = tracer.get_pii_flow_summary()
        data["sources"] = [n.full_path for n in tracer.find_pii_sources()]
        data["sinks"] = [n.full_path for n in tracer.find_pii_sinks()]
        output = json.dumps(data, indent=2)

    if out:
        out.write_text(output + "\n", encoding="utf-8")
        click.echo(f"Lineage ({format}) saved to {out}")
    else:
        click.echo(output)


# ── MLOps gate commands ──
#
# `gate` provides pipeline-friendly PII gates: read a file or stdin, emit a JSON
# report (stdout or --report), and exit non-zero when PII crosses --fail-on.
# Designed to run in isolation (no external services for text/JSONL inputs).


def _build_gate_engine(patterns: Tuple[Path, ...]) -> Engine:
    """Load a registry (default patterns unless overridden) and build an Engine."""
    pattern_paths = [str(p) for p in patterns] if patterns else None
    return Engine(load_registry(paths=pattern_paths))


def _add_gate_options(f: Any) -> Any:
    """Attach the options shared by every `gate` subcommand."""
    f = click.option(
        "--ns",
        "--namespace",
        "namespaces",
        multiple=True,
        help="Namespaces to search (default: all)",
    )(f)
    f = click.option(
        "--patterns",
        "-p",
        type=click.Path(exists=True, path_type=Path),
        multiple=True,
        help="Pattern files to load (defaults if omitted)",
    )(f)
    f = click.option(
        "--report",
        "report_path",
        type=click.Path(path_type=Path),
        help="Write JSON report to this file (default: stdout)",
    )(f)
    f = click.option(
        "--fail-on",
        type=click.Choice(["low", "medium", "high", "critical"]),
        default="low",
        show_default=True,
        help="Minimum finding severity that triggers a non-zero exit",
    )(f)
    f = click.option(
        "--show-matches",
        is_flag=True,
        help="Include raw matched PII values in the report (off by default)",
    )(f)
    f = click.option(
        "--quiet",
        "-q",
        is_flag=True,
        help="Suppress the human-readable summary on stderr",
    )(f)
    return f


def _emit_gate(
    report: GateReport,
    report_path: Optional[Path],
    fail_on: str,
    quiet: bool,
) -> None:
    """Write the JSON report, print a summary to stderr, and exit with the gate code."""
    json_text = report.to_json()
    if report_path:
        report_path.write_text(json_text + "\n", encoding="utf-8")
    else:
        click.echo(json_text)

    if not quiet:
        triggered = report.gate_triggered(fail_on)
        status = "FAIL" if triggered else "PASS"
        click.echo(
            f"[{status}] {report.target}: {report.findings_count} finding(s) across "
            f"{report.items_with_pii}/{report.scanned_items} item(s); "
            f"max_severity={report.max_severity or 'none'}; fail_on={fail_on}",
            err=True,
        )
        if report.errors:
            for err in report.errors:
                click.echo(f"  error: {err}", err=True)

    sys.exit(report.exit_code(fail_on))


@main.group()
def gate() -> None:
    """PII gates for CI/MLOps pipelines (JSON report + exit code)."""
    pass


@gate.command("text")
@click.argument("source", required=False, default="-")
@_add_gate_options
def gate_text(
    source: str,
    namespaces: Tuple[str, ...],
    patterns: Tuple[Path, ...],
    report_path: Optional[Path],
    fail_on: str,
    show_matches: bool,
    quiet: bool,
) -> None:
    """Scan plain text from a FILE or stdin ('-', the default) for PII."""
    if source == "-":
        text = sys.stdin.read()
        label = "stdin"
    else:
        text = Path(source).read_text(encoding="utf-8")
        label = source

    engine = _build_gate_engine(patterns)
    report = scan_text(
        engine,
        text,
        source=label,
        namespaces=list(namespaces) or None,
        show_matches=show_matches,
    )
    _emit_gate(report, report_path, fail_on, quiet)


@gate.command("rag")
@click.argument("source", required=False, default="-")
@click.option(
    "--field",
    "fields",
    multiple=True,
    help="Record field(s) to scan (repeatable; defaults to common RAG fields)",
)
@_add_gate_options
def gate_rag(
    source: str,
    fields: Tuple[str, ...],
    namespaces: Tuple[str, ...],
    patterns: Tuple[Path, ...],
    report_path: Optional[Path],
    fail_on: str,
    show_matches: bool,
    quiet: bool,
) -> None:
    """Scan a JSONL file (or stdin) of RAG records for PII, one JSON object per line."""
    raw = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    label = "stdin" if source == "-" else source

    records: List[Any] = []
    parse_errors: List[str] = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            parse_errors.append(f"line {lineno}: invalid JSON ({e.msg})")

    engine = _build_gate_engine(patterns)
    from datadetector.mlops import DEFAULT_RAG_FIELDS

    report = scan_rag_records(
        engine,
        records,
        source=label,
        fields=fields or DEFAULT_RAG_FIELDS,
        namespaces=list(namespaces) or None,
        show_matches=show_matches,
    )
    report.errors.extend(parse_errors)
    _emit_gate(report, report_path, fail_on, quiet)


@gate.command("training-data")
@click.argument("source", required=True)
@click.option(
    "--backend",
    type=click.Choice(["jsonl", "huggingface"]),
    default="jsonl",
    show_default=True,
    help="Training-data backend",
)
@click.option(
    "--strategy",
    type=click.Choice(["metadata_only", "sample", "full"]),
    default="sample",
    show_default=True,
    help="Scan strategy",
)
@click.option("--limit", "-l", type=int, default=100, help="Sample limit per field")
@_add_gate_options
def gate_training_data(
    source: str,
    backend: str,
    strategy: str,
    limit: int,
    namespaces: Tuple[str, ...],
    patterns: Tuple[Path, ...],
    report_path: Optional[Path],
    fail_on: str,
    show_matches: bool,
    quiet: bool,
) -> None:
    """Scan a training-data SOURCE (JSONL path/dir or HuggingFace dataset id) for PII."""
    engine = _build_gate_engine(patterns)
    report = scan_training_data(
        engine,
        source,
        backend=backend,
        namespaces=list(namespaces) or None,
        sample_limit=limit,
        strategy=strategy,
        show_matches=show_matches,
    )
    _emit_gate(report, report_path, fail_on, quiet)


if __name__ == "__main__":
    main()
