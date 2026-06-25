import httpx
import asyncio
import re


async def search_crossref(query: str, limit: int = 10):
    url = "https://api.crossref.org/works"
    params = {"query": query, "rows": limit, "sort": "relevance"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = data.get("message", {}).get("items", [])
            results = []
            for item in items:
                doi = item.get("DOI", "")
                title = item.get("title", [""])[0] if item.get("title") else "Untitled"
                authors_list = item.get("author", [])
                authors = ", ".join(
                    [
                        f"{a.get('given', '')} {a.get('family', '')}".strip()
                        for a in authors_list[:5]
                    ]
                ) or "Unknown"
                year = ""
                if item.get("published-print"):
                    year = item["published-print"].get("date-parts", [[None]])[0][0]
                elif item.get("published-online"):
                    year = item["published-online"].get("date-parts", [[None]])[0][0]
                if year is None:
                    year = ""
                source = item.get("publisher", "") or item.get("container-title", [""])[0]
                abstract = item.get("abstract", "")
                if abstract:
                    abstract = re.sub(r"<[^>]+>", "", abstract)
                    if len(abstract) > 300:
                        abstract = abstract[:300] + "..."
                pdf_url = ""
                for link in item.get("link", []):
                    if link.get("content-type") == "application/pdf":
                        pdf_url = link.get("URL", "")
                        break
                is_oa = any(
                    link.get("content-type") == "application/pdf"
                    for link in item.get("link", [])
                )
                results.append({
                    "title": title,
                    "authors": str(year) if year else "",
                    "year": str(year) if year else "",
                    "doi": doi,
                    "source": source,
                    "abstract": abstract or "",
                    "pdf_url": pdf_url,
                    "is_open_access": is_oa,
                    "url": f"https://doi.org/{doi}" if doi else "",
                })
            return results
    except Exception:
        return []


async def search_semantic_scholar(query: str, limit: int = 10):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,externalIds,openAccessPdf,abstract,venue",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = data.get("data", [])
            results = []
            for item in items:
                doi = item.get("externalIds", {}).get("DOI", "")
                title = item.get("title", "Untitled")
                authors = ", ".join(
                    [a.get("name", "") for a in item.get("authors", [])[:5]]
                ) or "Unknown"
                year = item.get("year") or ""
                source = item.get("venue", "")
                abstract = item.get("abstract") or ""
                if abstract and len(abstract) > 300:
                    abstract = abstract[:300] + "..."
                pdf_info = item.get("openAccessPdf")
                pdf_url = pdf_info.get("url", "") if pdf_info else ""
                results.append({
                    "title": title,
                    "authors": authors,
                    "year": str(year) if year else "",
                    "doi": doi,
                    "source": source,
                    "abstract": abstract,
                    "pdf_url": pdf_url,
                    "is_open_access": bool(pdf_url),
                    "url": f"https://doi.org/{doi}" if doi else "",
                })
            return results
    except Exception:
        return []


async def fetch_paper_by_doi(doi: str):
    url = f"https://api.crossref.org/works/{doi}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                url2 = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
                params2 = {"fields": "title,authors,year,externalIds,openAccessPdf,abstract,venue"}
                resp2 = await client.get(url2, params=params2)
                if resp2.status_code != 200:
                    return None
                data = resp2.json()
                pdf_info = data.get("openAccessPdf")
                return {
                    "title": data.get("title", "Untitled"),
                    "authors": ", ".join(a.get("name", "") for a in data.get("authors", [])[:5]),
                    "year": str(data.get("year") or ""),
                    "doi": doi,
                    "source": data.get("venue", ""),
                    "abstract": (data.get("abstract") or "")[:500],
                    "pdf_url": pdf_info.get("url", "") if pdf_info else "",
                    "is_open_access": bool(pdf_info),
                }
            data = resp.json()
            item = data.get("message", {})
            title = item.get("title", [""])[0] if item.get("title") else "Untitled"
            authors_list = item.get("author", [])
            authors = ", ".join(
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in authors_list[:5]
            ) or "Unknown"
            year = ""
            if item.get("published-print"):
                year = item["published-print"].get("date-parts", [[None]])[0][0]
            elif item.get("published-online"):
                year = item["published-online"].get("date-parts", [[None]])[0][0]
            if year is None:
                year = ""
            source = item.get("publisher", "") or item.get("container-title", [""])[0]
            abstract = re.sub(r"<[^>]+>", "", item.get("abstract", ""))[:500]
            pdf_url = ""
            for link in item.get("link", []):
                if link.get("content-type") == "application/pdf":
                    pdf_url = link.get("URL", "")
                    break
            return {
                "title": title,
                "authors": authors,
                "year": str(year) if year else "",
                "doi": doi,
                "source": source,
                "abstract": abstract,
                "pdf_url": pdf_url,
                "is_open_access": bool(pdf_url),
            }
    except Exception:
        return None


async def search_papers(query: str, limit: int = 10):
    crossref_task = search_crossref(query, limit // 2)
    ss_task = search_semantic_scholar(query, limit // 2)
    crossref_results, ss_results = await asyncio.gather(
        crossref_task, ss_task, return_exceptions=True
    )
    if isinstance(crossref_results, Exception):
        crossref_results = []
    if isinstance(ss_results, Exception):
        ss_results = []
    seen_dois = set()
    combined = []
    for paper in ss_results + crossref_results:
        doi = paper.get("doi", "")
        if doi and doi in seen_dois:
            continue
        if doi:
            seen_dois.add(doi)
        combined.append(paper)
    return combined[:limit]
