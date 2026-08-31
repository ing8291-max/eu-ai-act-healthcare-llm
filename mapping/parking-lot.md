For filling "Invoked by" Need to find "ALL Annex" 

Need codes like below.

text = fetch(consolidated_url)
for annex in annexes:
    hits = find_all(f"Annex {annex}", text)
    print(annex, [article_of(h) for h in hits])

annex-reference-mapper
