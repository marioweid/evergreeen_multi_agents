"""
Evergreen Multi Agents - Weekly Report Generator

Generates weekly impact reports per customer.
"""

from datetime import datetime
from database import list_customers, search_roadmap, get_roadmap_stats


def generate_customer_report(customer) -> str:
    """Generate a report for a single customer."""
    products = [p.strip() for p in customer.products_used.split(",")]
    
    report = []
    report.append(f"## {customer.name}")
    report.append(f"**Priority:** {customer.priority}")
    report.append(f"**Products:** {customer.products_used}")
    report.append("")
    
    # Find relevant roadmap items
    all_items = []
    for product in products:
        results = search_roadmap(product, n_results=3)
        for result in results:
            metadata = result.get("metadata", {})
            all_items.append({
                "title": metadata.get("title", "Unknown"),
                "status": metadata.get("status", "Unknown"),
                "release_date": metadata.get("release_date", "TBD"),
                "product": product
            })
    
    if all_items:
        report.append("### Relevant Roadmap Updates:")
        for item in all_items[:5]:  # Limit to 5 per customer
            report.append(f"- **{item['title']}** ({item['status']}) - {item['release_date']}")
    else:
        report.append("*No relevant roadmap updates found.*")
    
    report.append("")
    return "\n".join(report)


def generate_weekly_report() -> str:
    """Generate a full weekly report for all customers."""
    customers = list_customers()
    stats = get_roadmap_stats()
    
    report = []
    report.append("# Evergreen Weekly Report")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"**Roadmap Items in Database:** {stats['total_items']}")
    report.append("")
    report.append("---")
    report.append("")
    
    if not customers:
        report.append("*No customers in the database.*")
        return "\n".join(report)
    
    # Generate report by priority
    high_priority = [c for c in customers if c.priority == "high"]
    medium_priority = [c for c in customers if c.priority == "medium"]
    low_priority = [c for c in customers if c.priority == "low"]
    
    if high_priority:
        report.append("# 🔴 High Priority Customers\n")
        for customer in high_priority:
            report.append(generate_customer_report(customer))
    
    if medium_priority:
        report.append("# 🟡 Medium Priority Customers\n")
        for customer in medium_priority:
            report.append(generate_customer_report(customer))
    
    if low_priority:
        report.append("# 🟢 Low Priority Customers\n")
        for customer in low_priority:
            report.append(generate_customer_report(customer))
    
    return "\n".join(report)


def save_weekly_report(output_path: str = None) -> str:
    """Generate and save the weekly report."""
    if output_path is None:
        from pathlib import Path
        reports_dir = Path(__file__).parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d")
        output_path = reports_dir / f"weekly_report_{timestamp}.md"
    
    report = generate_weekly_report()
    
    with open(output_path, "w") as f:
        f.write(report)
    
    return f"Report saved to: {output_path}"


if __name__ == "__main__":
    from rich.console import Console
    from rich.markdown import Markdown
    
    console = Console()
    report = generate_weekly_report()
    console.print(Markdown(report))
