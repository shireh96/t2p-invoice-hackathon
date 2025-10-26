"""
NGO-InvoiceFiler: Command-Line Interface
Interactive CLI for processing documents, querying ledger, and exporting data.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional
import json

from main import InvoiceFilerOrchestrator, create_default_org_profile
from ledger import ReportGenerator


def print_banner():
    """Print application banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║            NGO-InvoiceFiler v1.0                             ║
║   Invoice & Receipt Processing System for NGOs               ║
║   OCR • Validation • Filing • Ledger Management              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_summary(result: dict):
    """Print processing summary"""
    if not result['success']:
        print(f"\n❌ PROCESSING FAILED")
        print(f"Error: {result.get('error', 'Unknown error')}")
        return

    print(f"\n✅ PROCESSING COMPLETE")
    print(f"Document ID: {result['doc_id']}")
    print(f"\n📄 Summary:")
    print(f"   {result['summary']}")
    print(f"\n📁 Filing:")
    print(f"   Folder: {result['folder_path']}")
    print(f"   File:   {result['file_name']}")

    # Show flags if any
    doc = result['processed_document']
    flags = doc['validation']['flags']
    if flags:
        print(f"\n⚠ Validation Flags ({len(flags)}):")
        for flag in flags[:5]:  # Show first 5
            severity_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
            icon = severity_icon.get(flag['severity'], '⚪')
            print(f"   {icon} [{flag['severity'].upper()}] {flag['message']}")
        if len(flags) > 5:
            print(f"   ... and {len(flags) - 5} more")


def print_dev_log(dev_log: list):
    """Print developer log"""
    print(f"\n🔧 Developer Log:")
    for entry in dev_log:
        print(f"   {entry}")


def cmd_process(args, orchestrator: InvoiceFilerOrchestrator):
    """Process a document"""
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        return

    print(f"📥 Processing: {file_path.name}")

    # Read file
    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    # Build user hints
    user_hints = {}
    if args.project:
        user_hints['project_code'] = args.project
    if args.grant:
        user_hints['grant_code'] = args.grant

    # Process
    result = orchestrator.process_document(
        file_bytes=file_bytes,
        file_name=file_path.name,
        user_hints=user_hints,
        user_role=args.role or 'contributor'
    )

    # Print results
    print_summary(result)

    if args.verbose:
        print_dev_log(result['dev_log'])

    # Save full JSON if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result['processed_document'], f, indent=2, ensure_ascii=False)
        print(f"\n💾 Full document JSON saved to: {output_path}")


def cmd_export(args, orchestrator: InvoiceFilerOrchestrator):
    """Export ledger"""
    print(f"📤 Exporting ledger to {args.format.upper()}...")

    # Build filters
    filters = {}
    if args.project:
        filters['project_code'] = args.project
    if args.grant:
        filters['grant_code'] = args.grant
    if args.fiscal_year:
        filters['fiscal_year'] = args.fiscal_year
    if args.status:
        filters['status'] = args.status

    # Export
    try:
        output_file = orchestrator.export_ledger(
            format=args.format,
            output_file=args.output,
            filters=filters if filters else None
        )
        print(f"✅ Ledger exported to: {output_file}")

        # Show stats
        entries = orchestrator.ledger_manager.query(filters if filters else None)
        print(f"   Records: {len(entries)}")

    except Exception as e:
        print(f"❌ Export failed: {e}")


def cmd_query(args, orchestrator: InvoiceFilerOrchestrator):
    """Query ledger"""
    print(f"🔍 Querying ledger...")

    # Build filters
    filters = {}
    if args.project:
        filters['project_code'] = args.project
    if args.grant:
        filters['grant_code'] = args.grant
    if args.fiscal_year:
        filters['fiscal_year'] = args.fiscal_year
    if args.status:
        filters['status'] = args.status
    if args.vendor:
        filters['vendor'] = args.vendor

    # Query
    results = orchestrator.ledger_manager.query(filters if filters else None)

    print(f"\n📊 Results: {len(results)} document(s)")

    if not results:
        return

    # Print table
    print(f"\n{'Date':<12} {'Vendor':<25} {'Amount':<15} {'Project':<10} {'Status':<12}")
    print("-" * 80)

    for entry in results[:20]:  # Show first 20
        date_str = entry.get('issue_date', 'N/A')[:10]
        vendor = entry.get('vendor', 'Unknown')[:24]
        amount = f"{entry.get('grand_total', 0):.2f} {entry.get('currency', '')}"
        project = entry.get('project_code', 'N/A')[:9]
        status = entry.get('status', 'unknown')[:11]

        print(f"{date_str:<12} {vendor:<25} {amount:<15} {project:<10} {status:<12}")

    if len(results) > 20:
        print(f"\n... and {len(results) - 20} more. Use --export to save all results.")


def cmd_stats(args, orchestrator: InvoiceFilerOrchestrator):
    """Show ledger statistics"""
    print(f"📈 Ledger Statistics\n")

    stats = orchestrator.ledger_manager.get_summary_stats()

    print(f"Total Documents: {stats['total_documents']}")
    print(f"Total Amount:    ${stats['total_amount']:,.2f}")

    print(f"\nBy Status:")
    for status, count in stats['by_status'].items():
        print(f"   {status:<15} {count:>5} documents")

    print(f"\nBy Project:")
    for project, amount in sorted(stats['by_project'].items(), key=lambda x: x[1], reverse=True):
        print(f"   {project:<15} ${amount:>12,.2f}")

    print(f"\nBy Fiscal Year:")
    for fy, amount in sorted(stats['by_fiscal_year'].items()):
        print(f"   {fy:<15} ${amount:>12,.2f}")


def cmd_report(args, orchestrator: InvoiceFilerOrchestrator):
    """Generate report"""
    report_gen = ReportGenerator(orchestrator.ledger_manager)

    if args.fiscal_year:
        print(f"📊 Fiscal Year Report: {args.fiscal_year}\n")
        report = report_gen.generate_fiscal_year_report(args.fiscal_year)

        print(f"Summary:")
        print(f"   Total Documents: {report['summary']['total_documents']}")
        print(f"   Total Amount:    ${report['summary']['total_amount']:,.2f}")
        print(f"   Average Amount:  ${report['summary']['average_amount']:,.2f}")

        print(f"\nBy Project:")
        for proj, amt in sorted(report['by_project'].items(), key=lambda x: x[1], reverse=True):
            print(f"   {proj:<15} ${amt:>12,.2f}")

        print(f"\nBy Grant:")
        for grant, amt in sorted(report['by_grant'].items(), key=lambda x: x[1], reverse=True):
            print(f"   {grant:<15} ${amt:>12,.2f}")

        print(f"\nTop 10 Vendors:")
        for vendor, amt in report['top_vendors']:
            print(f"   {vendor:<30} ${amt:>12,.2f}")

    elif args.project:
        print(f"📊 Project Report: {args.project}\n")
        report = report_gen.generate_project_report(args.project)

        print(f"Total Documents: {report['total_documents']}")
        print(f"Total Amount:    ${report['total_amount']:,.2f}")

        print(f"\nBy Grant:")
        for grant, amt in report['by_grant'].items():
            print(f"   {grant:<15} ${amt:>12,.2f}")

        print(f"\nBy Category:")
        for cat, amt in sorted(report['by_category'].items(), key=lambda x: x[1], reverse=True):
            print(f"   {cat:<20} ${amt:>12,.2f}")


def cmd_approve(args, orchestrator: InvoiceFilerOrchestrator):
    """Approve a document"""
    print(f"✅ Approving document: {args.doc_id}")

    result = orchestrator.approve_document(
        doc_id=args.doc_id,
        approver_name=args.approver,
        user_role=args.role or 'approver'
    )

    if result['success']:
        print(f"✅ Document approved by {args.approver}")
        print(f"   Status: {result['status']}")
    else:
        print(f"❌ Approval failed: {result['error']}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='NGO-InvoiceFiler: Invoice & Receipt Processing System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output (dev logs)')
    parser.add_argument('--role', choices=['viewer', 'contributor', 'approver', 'admin'],
                       default='contributor', help='User role for permissions')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Process command
    process_parser = subparsers.add_parser('process', help='Process a document')
    process_parser.add_argument('file', help='Path to invoice/receipt file (PDF or image)')
    process_parser.add_argument('--project', help='Project code')
    process_parser.add_argument('--grant', help='Grant code')
    process_parser.add_argument('--output', '-o', help='Output JSON file path')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export ledger')
    export_parser.add_argument('--format', choices=['csv', 'xlsx', 'json'],
                              default='csv', help='Export format')
    export_parser.add_argument('--output', '-o', help='Output file path')
    export_parser.add_argument('--project', help='Filter by project code')
    export_parser.add_argument('--grant', help='Filter by grant code')
    export_parser.add_argument('--fiscal-year', help='Filter by fiscal year (YYYY-YYYY)')
    export_parser.add_argument('--status', help='Filter by status')

    # Query command
    query_parser = subparsers.add_parser('query', help='Query ledger')
    query_parser.add_argument('--project', help='Filter by project code')
    query_parser.add_argument('--grant', help='Filter by grant code')
    query_parser.add_argument('--fiscal-year', help='Filter by fiscal year (YYYY-YYYY)')
    query_parser.add_argument('--status', help='Filter by status')
    query_parser.add_argument('--vendor', help='Filter by vendor name')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show ledger statistics')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.add_argument('--fiscal-year', help='Fiscal year report (YYYY-YYYY)')
    report_parser.add_argument('--project', help='Project report')

    # Approve command
    approve_parser = subparsers.add_parser('approve', help='Approve a document')
    approve_parser.add_argument('doc_id', help='Document ID')
    approve_parser.add_argument('--approver', required=True, help='Approver name')

    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        return

    print_banner()

    # Initialize orchestrator
    org_profile = create_default_org_profile()
    orchestrator = InvoiceFilerOrchestrator(org_profile)

    # Route to command
    if args.command == 'process':
        cmd_process(args, orchestrator)
    elif args.command == 'export':
        cmd_export(args, orchestrator)
    elif args.command == 'query':
        cmd_query(args, orchestrator)
    elif args.command == 'stats':
        cmd_stats(args, orchestrator)
    elif args.command == 'report':
        cmd_report(args, orchestrator)
    elif args.command == 'approve':
        cmd_approve(args, orchestrator)


if __name__ == '__main__':
    main()
