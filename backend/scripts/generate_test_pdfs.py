"""
Test fixture generator for PDF files

Creates sample PDF files for ingestion testing.
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_sample_pdf(output_path: Path, title: str, page_texts: list):
    """
    Create a simple PDF with multiple pages.
    
    Args:
        output_path: Path to save PDF
        title: PDF title
        page_texts: List of text strings, one per page
    """
    c = canvas.Canvas(str(output_path), pagesize=letter)
    c.setTitle(title)
    
    for page_num, text in enumerate(page_texts, 1):
        # Add title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 750, title)
        
        # Add page number
        c.setFont("Helvetica", 10)
        c.drawString(72, 730, f"Page {page_num}")
        
        # Add content
        c.setFont("Helvetica", 12)
        
        # Split text into lines and draw
        y = 700
        lines = text.split('\n')
        for line in lines:
            # Handle long lines by wrapping
            words = line.split()
            current_line = ""
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if len(test_line) * 6 > 450:  # Approximate width check
                    c.drawString(72, y, current_line)
                    y -= 15
                    current_line = word
                else:
                    current_line = test_line
            
            if current_line:
                c.drawString(72, y, current_line)
                y -= 15
            
            if y < 100:  # New page if running out of space
                break
        
        c.showPage()
    
    c.save()


def generate_test_fixtures(fixtures_dir: Path):
    """Generate all test PDF fixtures."""
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Engineering - Deployment Guidelines
    create_sample_pdf(
        fixtures_dir / "deployment_guidelines.pdf",
        "Deployment Guidelines",
        [
            """This document describes the deployment process for production systems.

Prerequisites:
- Access to production environment
- Valid credentials
- Approved change request

Steps:
1. Review change request
2. Backup current state
3. Deploy changes
4. Verify deployment
5. Update documentation""",
            """Deployment Checklist:

Pre-deployment:
- Code review completed
- Tests passing
- Security scan completed
- Database migrations prepared

Deployment:
- Take snapshot
- Stop services
- Apply updates
- Restart services
- Verify health

Post-deployment:
- Monitor logs
- Check metrics
- Notify stakeholders""",
            """Rollback Procedure:

If deployment fails:
1. Stop affected services
2. Restore from snapshot
3. Restart services
4. Verify system health
5. Investigate failure
6. Document lessons learned"""
        ]
    )
    
    # 2. Engineering - Coding Standards
    create_sample_pdf(
        fixtures_dir / "coding_standards.pdf",
        "Coding Standards",
        [
            """Coding Standards

These standards ensure consistency and quality across our codebase.

Python Style:
- Follow PEP 8
- Use type hints
- Write docstrings
- Maximum line length: 100 characters

Code Organization:
- One class per file
- Group related functions
- Use meaningful names""",
            """Testing Requirements:

- Write unit tests for all new code
- Maintain >80% coverage
- Use pytest framework
- Mock external dependencies

Documentation:
- Document all public APIs
- Include usage examples
- Keep README updated
- Document breaking changes"""
        ]
    )
    
    # 3. Sales - Sales Playbook
    create_sample_pdf(
        fixtures_dir / "sales_playbook.pdf",
        "Sales Playbook",
        [
            """Sales Playbook

This playbook provides guidance for our sales team.

Discovery Questions:
- What are your current challenges?
- What is your timeline?
- What is your budget?
- Who are the decision makers?

Value Proposition:
Our solution helps you:
- Increase efficiency by 40%
- Reduce costs by 30%
- Improve customer satisfaction""",
            """Objection Handling:

Price Concerns:
- Focus on ROI
- Highlight long-term value
- Offer payment plans

Competition:
- Know competitor weaknesses
- Emphasize unique features
- Share success stories

Closing Techniques:
- Trial close early
- Create urgency
- Summarize benefits"""
        ]
    )
    
    # 4. HR - Employee Handbook  
    create_sample_pdf(
        fixtures_dir / "employee_handbook.pdf",
        "Employee Handbook",
        [
            """Employee Handbook

Welcome to the company!

Work Hours:
- Standard: 9 AM - 5 PM
- Flexible hours available
- Core hours: 10 AM - 3 PM

Benefits:
- Health insurance
- 401(k) matching
- Paid time off
- Professional development budget""",
            """Code of Conduct:

Professional Behavior:
- Treat everyone with respect
- Maintain confidentiality
- Avoid conflicts of interest

Communication:
- Be responsive
- Use appropriate channels
- Keep managers informed

Remote Work Policy:
- Available after 90 days
- Requires manager approval
- Must maintain productivity"""
        ]
    )
    
    # 5. Empty PDF for testing
    create_sample_pdf(
        fixtures_dir / "empty_valid.pdf",
        "Empty Document",
        [""]  # This will fail the empty document check
    )
    
    print(f"✓ Created test fixtures in {fixtures_dir}")


if __name__ == "__main__":
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "pdfs"
    generate_test_fixtures(fixtures_dir)
