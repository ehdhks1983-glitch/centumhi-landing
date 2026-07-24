"""1화면 GUI + 등록 팝업 (개발명령서 v1.1 — 그래프 대신 텍스트 이력 리스트)"""
import threading

import customtkinter as ctk

import db
import tracker

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class RegisterPopup(ctk.CTkToplevel):
    """등록 팝업: 상품명 + (선택)몰명 + 키워드만. API 호출 0회 (§3)."""

    def __init__(self, master, on_saved):
        super().__init__(master)
        self.on_saved = on_saved
        self.title("상품 등록")
        self.geometry("420x420")
        self.grab_set()

        ctk.CTkLabel(self, text="상품명 *").pack(anchor="w", padx=16, pady=(16, 0))
        self.name_entry = ctk.CTkEntry(self, width=380)
        self.name_entry.pack(padx=16)

        ctk.CTkLabel(self, text="몰명 (선택 — 동명 타셀러 구분)").pack(anchor="w", padx=16, pady=(8, 0))
        self.mall_entry = ctk.CTkEntry(self, width=380)
        self.mall_entry.pack(padx=16)

        ctk.CTkLabel(self, text="상품 링크 (선택)").pack(anchor="w", padx=16, pady=(8, 0))
        self.link_entry = ctk.CTkEntry(self, width=380)
        self.link_entry.pack(padx=16)

        ctk.CTkLabel(self, text="추적 범위 (100~1000, 100 단위)").pack(anchor="w", padx=16, pady=(8, 0))
        self.limit_entry = ctk.CTkEntry(self, width=380)
        self.limit_entry.insert(0, "100")
        self.limit_entry.pack(padx=16)

        ctk.CTkLabel(self, text="키워드 (줄바꿈 또는 쉼표로 구분) *").pack(anchor="w", padx=16, pady=(8, 0))
        self.kw_box = ctk.CTkTextbox(self, width=380, height=90)
        self.kw_box.pack(padx=16)

        self.msg = ctk.CTkLabel(self, text="", text_color="tomato")
        self.msg.pack(pady=(4, 0))
        ctk.CTkButton(self, text="등록", command=self.save).pack(pady=8)

    def save(self):
        name = self.name_entry.get().strip()
        raw = self.kw_box.get("1.0", "end").replace(",", "\n")
        keywords = [k.strip() for k in raw.splitlines() if k.strip()]
        if not name or not keywords:
            self.msg.configure(text="상품명과 키워드는 필수입니다")
            return
        try:
            limit = max(1, min(1000, int(self.limit_entry.get().strip() or "100")))
        except ValueError:
            limit = 100
        db.add_product(
            name,
            mall_name=self.mall_entry.get().strip(),
            product_link=self.link_entry.get().strip(),
            track_limit=limit,
            keywords=keywords,
        )
        self.on_saved()
        self.destroy()


class App(ctk.CTk):
    def __init__(self, scheduler=None, reschedule=None):
        super().__init__()
        self.scheduler = scheduler
        self.reschedule = reschedule
        self._checking = False
        self.title("네이버 순위추적기 v1.1")
        self.geometry("860x640")

        # ── 상단: API 키 + 조회 시각 설정 ──
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(top, text="Client ID").grid(row=0, column=0, padx=(12, 4), pady=8)
        self.cid_entry = ctk.CTkEntry(top, width=160)
        self.cid_entry.insert(0, db.get_setting("client_id", "") or "")
        self.cid_entry.grid(row=0, column=1)

        ctk.CTkLabel(top, text="Client Secret").grid(row=0, column=2, padx=(12, 4))
        self.csec_entry = ctk.CTkEntry(top, width=160, show="*")
        self.csec_entry.insert(0, db.get_setting("client_secret", "") or "")
        self.csec_entry.grid(row=0, column=3)

        ctk.CTkLabel(top, text="자동 조회 시각(시)").grid(row=0, column=4, padx=(12, 4))
        self.hour_entry = ctk.CTkEntry(top, width=50)
        self.hour_entry.insert(0, db.get_setting("check_hour", "9") or "9")
        self.hour_entry.grid(row=0, column=5)

        ctk.CTkButton(top, text="설정 저장", width=90, command=self.save_settings).grid(
            row=0, column=6, padx=12
        )

        # ── 중단: 버튼 줄 ──
        btns = ctk.CTkFrame(self)
        btns.pack(fill="x", padx=12, pady=6)
        ctk.CTkButton(btns, text="+ 상품 등록", command=self.open_register).pack(side="left", padx=8, pady=8)
        self.check_btn = ctk.CTkButton(btns, text="지금 조회", command=self.run_now)
        self.check_btn.pack(side="left", padx=8)
        ctk.CTkButton(btns, text="선택 상품 삭제", fg_color="#8a3a3a", hover_color="#a04545",
                      command=self.delete_selected).pack(side="left", padx=8)
        self.usage_label = ctk.CTkLabel(btns, text="")
        self.usage_label.pack(side="right", padx=12)

        # ── 본문: 좌측 상품/키워드 목록, 우측 텍스트 이력 ──
        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=12, pady=6)

        self.product_list = ctk.CTkScrollableFrame(body, label_text="상품 · 키워드 (클릭 시 이력 표시)")
        self.product_list.pack(side="left", fill="both", expand=True, padx=(0, 6))

        right = ctk.CTkFrame(body)
        right.pack(side="right", fill="both", expand=True, padx=(6, 0))
        ctk.CTkLabel(right, text="순위 이력").pack(anchor="w", padx=8, pady=(8, 0))
        self.history_box = ctk.CTkTextbox(right, state="disabled")
        self.history_box.pack(fill="both", expand=True, padx=8, pady=8)

        # ── 하단: 로그 ──
        self.log_box = ctk.CTkTextbox(self, height=120, state="disabled")
        self.log_box.pack(fill="x", padx=12, pady=(6, 12))

        self.selected_product_id = None
        self.refresh()

    # ---------- helpers ----------

    def log(self, msg):
        def _append():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, _append)

    def save_settings(self):
        db.set_setting("client_id", self.cid_entry.get().strip())
        db.set_setting("client_secret", self.csec_entry.get().strip())
        try:
            hour = max(0, min(23, int(self.hour_entry.get().strip())))
        except ValueError:
            hour = 9
        db.set_setting("check_hour", str(hour))
        if self.reschedule:
            self.reschedule(hour)
        self.log(f"설정 저장 완료 (자동 조회 {hour:02d}:00)")

    def open_register(self):
        RegisterPopup(self, on_saved=self.refresh)

    def delete_selected(self):
        if self.selected_product_id is None:
            self.log("삭제할 상품을 먼저 클릭하세요")
            return
        db.delete_product(self.selected_product_id)
        self.selected_product_id = None
        self.refresh()
        self.log("상품 삭제 완료")

    def run_now(self):
        if self._checking:
            return
        self._checking = True
        self.check_btn.configure(state="disabled", text="조회 중…")

        def worker():
            try:
                tracker.run_all_checks(log=self.log)
            finally:
                self._checking = False
                self.after(0, lambda: (self.check_btn.configure(state="normal", text="지금 조회"),
                                       self.refresh()))

        threading.Thread(target=worker, daemon=True).start()

    # ---------- rendering ----------

    def refresh(self):
        for w in self.product_list.winfo_children():
            w.destroy()

        for product in db.get_all_products():
            pid = product["id"]
            tag = "●" if product["is_active"] else "○"
            nv = " [nvmid✓]" if product["nvmid"] else ""
            header = ctk.CTkButton(
                self.product_list,
                text=f"{tag} {product['product_name']}"
                     f"{' — ' + product['mall_name'] if product['mall_name'] else ''}{nv}",
                anchor="w", fg_color="transparent", border_width=1,
                command=lambda p=pid: self.select_product(p),
            )
            header.pack(fill="x", pady=(6, 2))

            for kw in db.get_keywords(pid):
                latest = db.get_latest_rank(kw["id"])
                if latest is None:
                    status = "미조회"
                elif latest["rank"] is None:
                    status = f"{product['track_limit']}위 내 없음 ({latest['checked_date']})"
                else:
                    status = f"{latest['rank']}위 ({latest['checked_date']}, {latest['match_method']})"
                row = ctk.CTkButton(
                    self.product_list,
                    text=f"    {kw['keyword']}  →  {status}",
                    anchor="w", fg_color="transparent", hover_color=("gray85", "gray25"),
                    command=lambda p=pid, k=kw["id"], name=kw["keyword"]: self.show_history(p, k, name),
                )
                row.pack(fill="x")

        self.usage_label.configure(text=f"오늘 API 사용량: {db.get_today_usage()}")

    def select_product(self, product_id):
        self.selected_product_id = product_id
        self.log(f"상품 #{product_id} 선택됨 (삭제 버튼 활성 대상)")

    def show_history(self, product_id, keyword_id, keyword_name):
        self.selected_product_id = product_id
        lines = [f"키워드: {keyword_name}", "-" * 34]
        for row in db.get_history(keyword_id):
            rank = f"{row['rank']}위" if row["rank"] is not None else "미발견"
            lines.append(f"{row['checked_date']}  {rank:>8}  ({row['match_method']})")
        if len(lines) == 2:
            lines.append("이력 없음")
        self.history_box.configure(state="normal")
        self.history_box.delete("1.0", "end")
        self.history_box.insert("1.0", "\n".join(lines))
        self.history_box.configure(state="disabled")
