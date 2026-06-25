import asyncio
import logging
from src.database import init_db, get_connection, add_paper, paper_exists_by_doi
from src.search import search_papers
from src.seed_data import seed_sections, SECTION_KEYWORDS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def get_leaf_sections():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sections WHERE id NOT IN (SELECT DISTINCT parent_id FROM sections WHERE parent_id IS NOT NULL)")
    rows = cursor.fetchall()
    conn.close()
    return [row["id"] for row in rows]


async def seed_all():
    init_db()
    seed_sections()

    leaf_ids = get_leaf_sections()
    total_added = 0
    total_skipped = 0

    conn = get_connection()
    cursor = conn.cursor()

    for sec_id in leaf_ids:
        cursor.execute("SELECT id, name_en, name_ar FROM sections WHERE id = ?", (sec_id,))
        sec = cursor.fetchone()
        if not sec:
            continue
        name_en = sec["name_en"]
        name_ar = sec["name_ar"]
        keyword = SECTION_KEYWORDS.get(name_en, name_en)
        log.info(f"🌱 جلب بحوث: {name_ar} ({keyword})")
        results = await search_papers(keyword, limit=7)
        added = 0
        skipped = 0
        for paper in results:
            doi = paper.get("doi", "")
            if doi and paper_exists_by_doi(doi):
                skipped += 1
                continue
            add_paper(
                section_id=sec_id,
                title=paper["title"],
                authors=paper["authors"],
                year=paper["year"],
                doi=doi,
                url=paper.get("url", ""),
                abstract=paper["abstract"],
                source=paper.get("source", ""),
                pdf_url=paper.get("pdf_url", ""),
                is_open_access=1 if paper.get("is_open_access") else 0,
            )
            added += 1
        total_added += added
        total_skipped += skipped
        log.info(f"   ✅ {added} مضاف | ⏭️ {skipped} مكرر")

    conn.close()
    log.info(f"\n{'='*40}")
    log.info(f"تم الانتهاء!")
    log.info(f"✅ إجمالي مضاف: {total_added}")
    log.info(f"⏭️ إجمالي مكرر: {total_skipped}")
    log.info(f"{'='*40}")


if __name__ == "__main__":
    asyncio.run(seed_all())
