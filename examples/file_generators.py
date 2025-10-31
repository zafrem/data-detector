#!/usr/bin/env python3
"""
Utility functions for generating various output files in examples.

This module provides reusable functions that demonstrate file generation
capabilities without creating files in the current directory.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from datadetector import (
    BulkDataGenerator,
    FakeDataGenerator,
    OfficeFileGenerator,
    ImageGenerator,
    PDFGenerator,
    XMLGenerator,
)


class FileGenerationManager:
    """A utility class for managing file generation in examples."""
    
    def __init__(self, temp_dir: Optional[str] = None, seed: int = 12345):
        """Initialize with optional temporary directory and seed."""
        self.temp_dir = temp_dir or tempfile.mkdtemp()
        self.seed = seed
        self.generator = FakeDataGenerator(seed=seed)
        self.bulk_gen = BulkDataGenerator(seed=seed)
        self.generated_files = []
    
    def get_output_path(self, filename: str) -> Path:
        """Get full path for output file in temp directory."""
        path = Path(self.temp_dir) / filename
        self.generated_files.append(str(path))
        return path
    
    def generate_basic_data(self) -> Dict[str, Any]:
        """Generate basic fake data samples."""
        return {
            "email": self.generator.from_pattern("comm/email_01"),
            "phone": self.generator.from_pattern("comm/phone_us_01"),
            "ssn": self.generator.from_pattern("us/ssn_01"),
            "credit_card": self.generator.from_pattern("comm/credit_card_visa_01"),
            "aws_key": self.generator.from_pattern("comm/aws_access_key_01")
        }
    
    def create_csv_file(self, filename: str = "output.csv", rows: int = 100) -> Dict[str, Any]:
        """Create CSV file with fake data."""
        output_path = self.get_output_path(filename)
        self.generator.create_csv_file(str(output_path), rows=rows, include_pii=True)
        
        file_size = output_path.stat().st_size
        return {
            "file_path": str(output_path),
            "rows": rows,
            "file_size": file_size,
            "size_mb": file_size / 1024 / 1024
        }
    
    def create_json_file(self, filename: str = "output.json", records: int = 50) -> Dict[str, Any]:
        """Create JSON file with fake data."""
        output_path = self.get_output_path(filename)
        self.generator.create_json_file(str(output_path), records=records, include_pii=True)
        
        file_size = output_path.stat().st_size
        return {
            "file_path": str(output_path),
            "records": records,
            "file_size": file_size,
            "size_mb": file_size / 1024 / 1024
        }
    
    def create_sqlite_file(self, filename: str = "output.db", records: int = 200) -> Dict[str, Any]:
        """Create SQLite database with fake data."""
        output_path = self.get_output_path(filename)
        self.generator.create_sqlite_file(str(output_path), records=records, include_pii=True)
        
        file_size = output_path.stat().st_size
        return {
            "file_path": str(output_path),
            "records": records,
            "file_size": file_size,
            "size_mb": file_size / 1024 / 1024
        }
    
    def create_log_file(self, filename: str = "output.log", lines: int = 1000, log_format: str = "apache") -> Dict[str, Any]:
        """Create log file with fake data."""
        output_path = self.get_output_path(filename)
        self.generator.create_log_file(str(output_path), lines=lines, log_format=log_format)
        
        file_size = output_path.stat().st_size
        return {
            "file_path": str(output_path),
            "lines": lines,
            "format": log_format,
            "file_size": file_size,
            "size_mb": file_size / 1024 / 1024
        }
    
    def create_office_files(self) -> Dict[str, Any]:
        """Create Office files (Word, Excel, PowerPoint)."""
        results = {}
        
        try:
            office_gen = OfficeFileGenerator(self.generator)
            
            # Word file
            word_path = self.get_output_path("output.docx")
            office_gen.create_word_file(str(word_path), paragraphs=10)
            results["word"] = {
                "file_path": str(word_path),
                "paragraphs": 10,
                "file_size": word_path.stat().st_size,
                "success": True
            }
            
            # Excel file
            excel_path = self.get_output_path("output.xlsx")
            office_gen.create_excel_file(str(excel_path), rows=500)
            results["excel"] = {
                "file_path": str(excel_path),
                "rows": 500,
                "file_size": excel_path.stat().st_size,
                "success": True
            }
            
            # PowerPoint file
            ppt_path = self.get_output_path("output.pptx")
            office_gen.create_powerpoint_file(str(ppt_path), slides=5)
            results["powerpoint"] = {
                "file_path": str(ppt_path),
                "slides": 5,
                "file_size": ppt_path.stat().st_size,
                "success": True
            }
            
        except ImportError as e:
            results["error"] = f"Missing dependencies: {e}"
            results["success"] = False
        
        return results
    
    def create_image_file(self, filename: str = "output.png", width: int = 800, height: int = 600) -> Dict[str, Any]:
        """Create image file with text."""
        try:
            img_gen = ImageGenerator(self.generator)
            output_path = self.get_output_path(filename)
            img_gen.create_image_with_text(str(output_path), width=width, height=height)
            
            file_size = output_path.stat().st_size
            return {
                "file_path": str(output_path),
                "width": width,
                "height": height,
                "file_size": file_size,
                "success": True
            }
        except ImportError as e:
            return {
                "error": f"Missing Pillow dependency: {e}",
                "success": False
            }
    
    def create_pdf_files(self) -> Dict[str, Any]:
        """Create PDF files."""
        results = {}
        
        try:
            pdf_gen = PDFGenerator(self.generator)
            
            # Regular PDF
            pdf_path = self.get_output_path("output.pdf")
            pdf_gen.create_pdf_file(str(pdf_path), pages=5)
            results["pdf"] = {
                "file_path": str(pdf_path),
                "pages": 5,
                "file_size": pdf_path.stat().st_size,
                "success": True
            }
            
            # Invoice PDF
            invoice_path = self.get_output_path("invoice.pdf")
            pdf_gen.create_pdf_invoice(str(invoice_path))
            results["invoice"] = {
                "file_path": str(invoice_path),
                "file_size": invoice_path.stat().st_size,
                "success": True
            }
            
        except ImportError as e:
            results["error"] = f"Missing reportlab dependency: {e}"
            results["success"] = False
        
        return results
    
    def create_xml_file(self, filename: str = "output.xml", records: int = 50) -> Dict[str, Any]:
        """Create XML file with fake data."""
        xml_gen = XMLGenerator(self.generator)
        output_path = self.get_output_path(filename)
        xml_gen.create_xml_file(str(output_path), records=records)
        
        file_size = output_path.stat().st_size
        return {
            "file_path": str(output_path),
            "records": records,
            "file_size": file_size,
            "size_mb": file_size / 1024 / 1024
        }
    
    def create_bulk_training_data(self) -> Dict[str, Any]:
        """Create bulk training data in various formats."""
        results = {}
        
        # JSONL format
        jsonl_path = self.get_output_path("training_data.jsonl")
        self.bulk_gen.save_bulk_data_jsonl(
            jsonl_path,
            num_records=1000,
            patterns_per_record=(3, 8),
        )
        
        # Sample record
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            sample = json.loads(f.readline())
        
        results["jsonl"] = {
            "file_path": str(jsonl_path),
            "records": 1000,
            "file_size": jsonl_path.stat().st_size,
            "size_mb": jsonl_path.stat().st_size / 1024 / 1024,
            "sample_record_id": sample['record_id'],
            "sample_pii_count": len(sample['pii_items'])
        }
        
        # JSON format
        json_path = self.get_output_path("training_data.json")
        self.bulk_gen.save_bulk_data_json(
            json_path,
            num_records=500,
            patterns_per_record=(2, 6),
        )
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results["json"] = {
            "file_path": str(json_path),
            "records": data['metadata']['num_records'],
            "file_size": json_path.stat().st_size,
            "size_mb": json_path.stat().st_size / 1024 / 1024,
            "metadata": data['metadata']
        }
        
        # CSV format
        csv_path = self.get_output_path("training_data.csv")
        self.bulk_gen.save_bulk_data_csv(
            csv_path,
            num_records=200,
            patterns_per_record=(1, 5),
        )
        
        # Preview CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            header = f.readline().strip()
            first_row = f.readline().strip()
        
        results["csv"] = {
            "file_path": str(csv_path),
            "records": 200,
            "file_size": csv_path.stat().st_size,
            "size_mb": csv_path.stat().st_size / 1024 / 1024,
            "header": header,
            "sample_row": first_row[:100] + "..." if len(first_row) > 100 else first_row
        }
        
        return results
    
    def create_large_dataset(self, records: int = 10000) -> Dict[str, Any]:
        """Create large training dataset."""
        output_path = self.get_output_path("training_data_large.jsonl")
        
        self.bulk_gen.save_bulk_data_jsonl(
            output_path,
            num_records=records,
            patterns_per_record=(3, 10),
        )
        
        # Sample analysis
        sample_size = 100
        total_pii = 0
        
        with open(output_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= sample_size:
                    break
                record = json.loads(line)
                total_pii += len(record['pii_items'])
        
        avg_pii = total_pii / sample_size
        
        file_size = output_path.stat().st_size
        return {
            "file_path": str(output_path),
            "records": records,
            "file_size": file_size,
            "size_mb": file_size / 1024 / 1024,
            "sample_size": sample_size,
            "avg_pii_per_record": avg_pii
        }
    
    def generate_all_files(self) -> Dict[str, Any]:
        """Generate all types of files."""
        results = {}
        
        # Basic data
        results["basic_data"] = self.generate_basic_data()
        
        # File types
        results["csv"] = self.create_csv_file()
        results["json"] = self.create_json_file()
        results["sqlite"] = self.create_sqlite_file()
        results["log"] = self.create_log_file()
        results["office"] = self.create_office_files()
        results["image"] = self.create_image_file()
        results["pdf"] = self.create_pdf_files()
        results["xml"] = self.create_xml_file()
        results["bulk_training"] = self.create_bulk_training_data()
        
        return results
    
    def cleanup(self) -> List[str]:
        """Clean up generated files."""
        cleaned_files = []
        
        for file_path in self.generated_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                cleaned_files.append(file_path)
        
        # Try to remove temp directory if empty
        try:
            os.rmdir(self.temp_dir)
            cleaned_files.append(self.temp_dir)
        except OSError:
            pass  # Directory not empty or doesn't exist
        
        return cleaned_files
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of generated files."""
        total_size = 0
        file_count = 0
        
        for file_path in self.generated_files:
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
                file_count += 1
        
        return {
            "temp_directory": self.temp_dir,
            "total_files": file_count,
            "total_size": total_size,
            "total_size_mb": total_size / 1024 / 1024,
            "generated_files": self.generated_files
        }


def run_quick_demo() -> Dict[str, Any]:
    """Run a quick demonstration of file generation."""
    manager = FileGenerationManager()
    
    try:
        results = {}
        results["basic_data"] = manager.generate_basic_data()
        results["csv"] = manager.create_csv_file(rows=50)
        results["json"] = manager.create_json_file(records=25)
        results["xml"] = manager.create_xml_file(records=25)
        results["summary"] = manager.get_summary()
        
        return results
    finally:
        results["cleanup"] = manager.cleanup()
        return results


def run_full_demo() -> Dict[str, Any]:
    """Run full demonstration of all file generation capabilities."""
    manager = FileGenerationManager()
    
    try:
        results = manager.generate_all_files()
        results["summary"] = manager.get_summary()
        
        return results
    finally:
        results["cleanup"] = manager.cleanup()
        return results
