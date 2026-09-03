"""SQLite Storage Engine for TrulyTally AI with Deterministic HITL Write Safety."""

from __future__ import annotations
import sqlite3
import json
import os
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime


DB_PATH = os.environ.get("DB_PATH", "truly_tally.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn


def init_db():
    """Initializes database tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Invoices table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        content_type TEXT,
        status TEXT DEFAULT 'uploaded',
        triage_status TEXT DEFAULT 'needs_attention',
        confidence_score REAL DEFAULT 0.0,
        invoice_number TEXT,
        invoice_date TEXT,
        party_name TEXT,
        party_gstin TEXT,
        taxable_value REAL DEFAULT 0.0,
        total_tax REAL DEFAULT 0.0,
        grand_total REAL DEFAULT 0.0,
        extracted_data_json TEXT,
        raw_markdown TEXT,
        tally_xml TEXT,
        sync_status TEXT DEFAULT 'pending',
        voucher_number TEXT,
        synced_at TEXT,
        error_message TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # Bank Statements table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bank_statements (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        bank_name TEXT,
        account_number TEXT,
        account_type TEXT,
        tally_bank_ledger TEXT,
        period_start TEXT,
        period_end TEXT,
        opening_balance REAL DEFAULT 0.0,
        closing_balance REAL DEFAULT 0.0,
        total_debits REAL DEFAULT 0.0,
        total_credits REAL DEFAULT 0.0,
        transaction_count INTEGER DEFAULT 0,
        raw_markdown TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # Bank Transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bank_transactions (
        id TEXT PRIMARY KEY,
        statement_id TEXT NOT NULL,
        transaction_date TEXT NOT NULL,
        narration TEXT NOT NULL,
        chq_ref_no TEXT,
        withdrawal_dr REAL DEFAULT 0.0,
        deposit_cr REAL DEFAULT 0.0,
        balance REAL DEFAULT 0.0,
        suggested_voucher_type TEXT DEFAULT 'Payment',
        matched_counter_ledger TEXT,
        approval_status TEXT DEFAULT 'staged',
        FOREIGN KEY(statement_id) REFERENCES bank_statements(id) ON DELETE CASCADE
    );
    """)

    # Deterministic Human-in-the-Loop (HITL) Approval Queue
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hitl_approval_queue (
        id TEXT PRIMARY KEY,
        action_type TEXT NOT NULL,
        reference_id TEXT NOT NULL,
        target_company TEXT DEFAULT 'Active Tally Company',
        description TEXT NOT NULL,
        payload_xml TEXT NOT NULL,
        payload_json TEXT,
        status TEXT DEFAULT 'PENDING_HUMAN_APPROVAL',
        created_at TEXT NOT NULL,
        reviewed_by TEXT,
        reviewed_at TEXT,
        error_message TEXT
    );
    """)

    # Connector Heartbeats table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS connector_heartbeats (
        client_id TEXT PRIMARY KEY,
        tally_online INTEGER DEFAULT 0,
        company_name TEXT,
        error_message TEXT,
        last_heartbeat TEXT
    );
    """)

    # Pending Sync Queue
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pending_sync_queue (
        invoice_id TEXT PRIMARY KEY,
        tally_xml TEXT NOT NULL,
        auto_masters_json TEXT,
        enqueued_at TEXT,
        attempts INTEGER DEFAULT 0
    );
    """)

    conn.commit()
    conn.close()


class InvoiceStore:
    """CRUD operations for invoices."""

    @staticmethod
    def save_invoice(
        id: str,
        filename: str,
        filepath: str,
        content_type: str,
        invoice_data: Optional[Dict[str, Any]] = None,
        tally_xml: Optional[str] = None,
        raw_markdown: Optional[str] = None,
        status: str = "uploaded"
    ):
        conn = get_db_connection()
        cursor = conn.cursor()

        data_json = json.dumps(invoice_data) if invoice_data else None
        now = datetime.utcnow().isoformat()

        inv_num = invoice_data.get("invoice_number") if invoice_data else None
        inv_date = invoice_data.get("invoice_date") if invoice_data else None
        party = invoice_data.get("supplier", {}).get("name") if invoice_data else None
        gstin = invoice_data.get("supplier", {}).get("gstin") if invoice_data else None

        summary = invoice_data.get("summary", {}) if invoice_data else {}
        taxable = summary.get("total_taxable_value", 0.0)
        tot_tax = summary.get("total_cgst", 0.0) + summary.get("total_sgst", 0.0) + summary.get("total_igst", 0.0)
        grand_total = summary.get("grand_total", 0.0)

        validation = invoice_data.get("validation", {}) if invoice_data else {}
        triage = validation.get("triage_status", "needs_attention")
        confidence = validation.get("confidence_score", 0.0)

        cursor.execute("""
        INSERT OR REPLACE INTO invoices (
            id, filename, filepath, content_type, status, triage_status,
            confidence_score, invoice_number, invoice_date, party_name,
            party_gstin, taxable_value, total_tax, grand_total,
            extracted_data_json, raw_markdown, tally_xml, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            id, filename, filepath, content_type, status, triage,
            confidence, inv_num, inv_date, party, gstin,
            taxable, tot_tax, grand_total, data_json, raw_markdown, tally_xml, now
        ))

        conn.commit()
        conn.close()

    @staticmethod
    def get_invoice(id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE id = ?", (id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        d = dict(row)
        if d.get("extracted_data_json"):
            try:
                d["invoice_data"] = json.loads(d["extracted_data_json"])
            except Exception:
                d["invoice_data"] = None
        return d

    @staticmethod
    def list_invoices(triage_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()

        if triage_filter and triage_filter != "all":
            if triage_filter == "synced":
                cursor.execute("SELECT * FROM invoices WHERE sync_status = 'synced' ORDER BY created_at DESC")
            else:
                cursor.execute(
                    "SELECT * FROM invoices WHERE triage_status = ? AND sync_status != 'synced' ORDER BY created_at DESC",
                    (triage_filter,)
                )
        else:
            cursor.execute("SELECT * FROM invoices ORDER BY created_at DESC")

        rows = cursor.fetchall()
        conn.close()

        results = []
        for r in rows:
            item = dict(r)
            if item.get("extracted_data_json"):
                try:
                    item["invoice_data"] = json.loads(item["extracted_data_json"])
                except Exception:
                    pass
            results.append(item)
        return results

    @staticmethod
    def update_sync_status(id: str, status: str, voucher_number: Optional[str] = None, error_message: Optional[str] = None):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        cursor.execute("""
        UPDATE invoices SET
            sync_status = ?,
            voucher_number = COALESCE(?, voucher_number),
            error_message = ?,
            synced_at = ?
        WHERE id = ?
        """, (status, voucher_number, error_message, now if status == "synced" else None, id))
        conn.commit()
        conn.close()

    @staticmethod
    def delete_invoice(id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoices WHERE id = ?", (id,))
        cursor.execute("DELETE FROM pending_sync_queue WHERE invoice_id = ?", (id,))
        cursor.execute("DELETE FROM hitl_approval_queue WHERE reference_id = ?", (id,))
        conn.commit()
        conn.close()


class BankStore:
    """CRUD operations for Bank Statements and Transactions."""

    @staticmethod
    def save_statement(
        statement_id: str,
        filename: str,
        filepath: str,
        statement_data: Dict[str, Any],
        raw_markdown: Optional[str] = None,
    ):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        txns = statement_data.get("transactions", [])
        cursor.execute("""
        INSERT OR REPLACE INTO bank_statements (
            id, filename, filepath, bank_name, account_number, account_type,
            tally_bank_ledger, period_start, period_end, opening_balance,
            closing_balance, total_debits, total_credits, transaction_count,
            raw_markdown, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            statement_id, filename, filepath,
            statement_data.get("bank_name"),
            statement_data.get("account_number"),
            statement_data.get("account_type", "Current Account"),
            statement_data.get("tally_bank_ledger", "Bank Account"),
            statement_data.get("period_start"),
            statement_data.get("period_end"),
            statement_data.get("opening_balance", 0.0),
            statement_data.get("closing_balance", 0.0),
            statement_data.get("total_debits", 0.0),
            statement_data.get("total_credits", 0.0),
            len(txns),
            raw_markdown,
            now
        ))

        # Save individual transactions
        for t in txns:
            cursor.execute("""
            INSERT OR REPLACE INTO bank_transactions (
                id, statement_id, transaction_date, narration, chq_ref_no,
                withdrawal_dr, deposit_cr, balance, suggested_voucher_type,
                matched_counter_ledger, approval_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                t.get("id") or str(uuid.uuid4())[:8],
                statement_id,
                t.get("transaction_date"),
                t.get("narration"),
                t.get("chq_ref_no"),
                t.get("withdrawal_dr", 0.0),
                t.get("deposit_cr", 0.0),
                t.get("balance", 0.0),
                t.get("suggested_voucher_type", "Payment"),
                t.get("matched_counter_ledger"),
                t.get("approval_status", "staged")
            ))

        conn.commit()
        conn.close()

    @staticmethod
    def list_statements() -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bank_statements ORDER BY created_at DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_statement_with_transactions(statement_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bank_statements WHERE id = ?", (statement_id,))
        st_row = cursor.fetchone()
        if not st_row:
            conn.close()
            return None

        statement = dict(st_row)
        cursor.execute("SELECT * FROM bank_transactions WHERE statement_id = ? ORDER BY transaction_date ASC", (statement_id,))
        statement["transactions"] = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return statement

    @staticmethod
    def update_transaction(txn_id: str, fields: Dict[str, Any]):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE bank_transactions SET
            suggested_voucher_type = COALESCE(?, suggested_voucher_type),
            matched_counter_ledger = COALESCE(?, matched_counter_ledger),
            approval_status = COALESCE(?, approval_status)
        WHERE id = ?
        """, (
            fields.get("suggested_voucher_type"),
            fields.get("matched_counter_ledger"),
            fields.get("approval_status"),
            txn_id
        ))
        conn.commit()
        conn.close()


class HitlStore:
    """Deterministic Human-in-the-Loop Write Safety Gateway."""

    @staticmethod
    def stage_write_action(
        action_type: str,
        reference_id: str,
        description: str,
        payload_xml: str,
        payload_json: Optional[Dict[str, Any]] = None,
        target_company: str = "Active Tally Company",
    ) -> str:
        """Stages a write action into the quarantined approval queue. ZERO write happens autonomously."""
        conn = get_db_connection()
        cursor = conn.cursor()
        approval_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        json_str = json.dumps(payload_json) if payload_json else None

        cursor.execute("""
        INSERT INTO hitl_approval_queue (
            id, action_type, reference_id, target_company, description,
            payload_xml, payload_json, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING_HUMAN_APPROVAL', ?)
        """, (approval_id, action_type, reference_id, target_company, description, payload_xml, json_str, now))

        conn.commit()
        conn.close()
        return approval_id

    @staticmethod
    def list_pending_approvals() -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hitl_approval_queue WHERE status = 'PENDING_HUMAN_APPROVAL' ORDER BY created_at ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def approve_action(approval_id: str, user: str = "Operator") -> Optional[Dict[str, Any]]:
        """Human operator explicitly signs off on write action, releasing it to the Tally queue."""
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()

        cursor.execute("SELECT * FROM hitl_approval_queue WHERE id = ?", (approval_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        record = dict(row)

        cursor.execute("""
        UPDATE hitl_approval_queue SET
            status = 'APPROVED',
            reviewed_by = ?,
            reviewed_at = ?
        WHERE id = ?
        """, (user, now, approval_id))
        conn.commit()
        conn.close()

        # Enqueue the approved XML into the Tally sync daemon queue
        TallyConnectorStore.enqueue_for_sync(
            invoice_id=record["reference_id"],
            tally_xml=record["payload_xml"],
        )

        return record

    @staticmethod
    def reject_action(approval_id: str, user: str = "Operator", reason: str = "Rejected by human reviewer"):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        cursor.execute("""
        UPDATE hitl_approval_queue SET
            status = 'REJECTED',
            reviewed_by = ?,
            reviewed_at = ?,
            error_message = ?
        WHERE id = ?
        """, (user, now, reason, approval_id))
        conn.commit()
        conn.close()


class TallyConnectorStore:
    """Tracks daemon heartbeats and pending sync queue."""

    @staticmethod
    def record_heartbeat(client_id: str, tally_online: bool, company_name: str, error: Optional[str] = None):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        cursor.execute("""
        INSERT OR REPLACE INTO connector_heartbeats (client_id, tally_online, company_name, error_message, last_heartbeat)
        VALUES (?, ?, ?, ?, ?)
        """, (client_id, 1 if tally_online else 0, company_name, error, now))
        conn.commit()
        conn.close()

    @staticmethod
    def get_latest_connector_status() -> Dict[str, Any]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM connector_heartbeats ORDER BY last_heartbeat DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {
                "online": False,
                "company_name": "No Connector Active",
                "last_seen": None,
                "error": "No local connector daemon detected. Run tally_connector.py or start Virtual Tally."
            }

        d = dict(row)
        last_dt = datetime.fromisoformat(d["last_heartbeat"])
        diff_seconds = (datetime.utcnow() - last_dt).total_seconds()
        is_active = (diff_seconds <= 15) and (d["tally_online"] == 1)

        return {
            "online": is_active,
            "company_name": d["company_name"] if is_active else "Disconnected",
            "last_seen": d["last_heartbeat"],
            "client_id": d["client_id"],
            "error": d["error_message"] if not is_active else None
        }

    @staticmethod
    def enqueue_for_sync(invoice_id: str, tally_xml: str, auto_masters: Optional[List[str]] = None):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat()
        masters_json = json.dumps(auto_masters or [])
        cursor.execute("""
        INSERT OR REPLACE INTO pending_sync_queue (invoice_id, tally_xml, auto_masters_json, enqueued_at)
        VALUES (?, ?, ?, ?)
        """, (invoice_id, tally_xml, masters_json, now))
        conn.commit()
        conn.close()

    @staticmethod
    def get_pending_sync_items() -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT q.invoice_id, q.tally_xml, q.auto_masters_json,
               COALESCE(i.invoice_number, 'TXN-' || q.invoice_id) as invoice_number,
               COALESCE(i.party_name, 'Bank/Party') as party_name
        FROM pending_sync_queue q
        LEFT JOIN invoices i ON q.invoice_id = i.id
        """)
        rows = cursor.fetchall()
        conn.close()

        items = []
        for r in rows:
            masters = []
            if r["auto_masters_json"]:
                try:
                    masters = json.loads(r["auto_masters_json"])
                except Exception:
                    pass
            items.append({
                "invoice_id": r["invoice_id"],
                "tally_xml": r["tally_xml"],
                "auto_masters_xml": masters,
                "invoice_number": r["invoice_number"],
                "party_name": r["party_name"]
            })
        return items

    @staticmethod
    def remove_from_pending(invoice_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pending_sync_queue WHERE invoice_id = ?", (invoice_id,))
        conn.commit()
        conn.close()


init_db()
