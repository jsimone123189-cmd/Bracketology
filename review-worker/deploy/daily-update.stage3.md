# Stage 3: changes to `.github/workflows/daily-update.yml` (apply only after approval)

In the `publish` job, add **after** "Restore saved game results" and **before** the `build` step:

```yaml
      - name: Private review (build, upload; never printed)
        continue-on-error: true            # the public site never waits on the private review
        run: |
          PYTHONPATH=src python -m bracketology.review build 2027 > /dev/null && echo "review built"
          PYTHONPATH=src python -m bracketology.review upload 2027
        env:
          BRACKETOLOGY_UA: "bracketology-bot/0.1 (free open bracketology project)"
          REVIEW_URL: ${{ secrets.REVIEW_URL }}
          CF_ACCESS_CLIENT_ID: ${{ secrets.CF_ACCESS_CLIENT_ID }}
          CF_ACCESS_CLIENT_SECRET: ${{ secrets.CF_ACCESS_CLIENT_SECRET }}
      - name: Published bracket (lines only; 404 = nothing published, the site shows the model)
        run: |
          code=$(curl -sS -o data/output/published_2027.json -w "%{http_code}" "$REVIEW_URL/api/machine/published?season=2027" \
                 -H "CF-Access-Client-Id: $CF_ACCESS_CLIENT_ID" -H "CF-Access-Client-Secret: $CF_ACCESS_CLIENT_SECRET") || code=000
          echo "published lines: HTTP $code"
          [ "$code" = "200" ] || rm -f data/output/published_2027.json
          if [ "$code" = "200" ] && python3 -c "import json,sys; d=json.load(open('data/output/published_2027.json')); sys.exit(0 if d.get('complete') is False else 1)"; then
            echo "::warning::The final snapshot was frozen before every conference final ended. The site labels it; see the review page."
            echo "incomplete_final=true" >> "$GITHUB_ENV"
          fi
        env:
          REVIEW_URL: ${{ secrets.REVIEW_URL }}
          CF_ACCESS_CLIENT_ID: ${{ secrets.CF_ACCESS_CLIENT_ID }}
          CF_ACCESS_CLIENT_SECRET: ${{ secrets.CF_ACCESS_CLIENT_SECRET }}
```

And as the **last** step of the job (after the Cloudflare deploy), so GitHub emails you while the page is still published:

```yaml
      - name: Alert if the final is incomplete
        if: env.incomplete_final == 'true'
        run: { echo "::error::Final snapshot is INCOMPLETE (labelled on the site). Check the review page."; exit 1; }
```

Also: merge branch `public-privacy` (it reads `data/output/published_2027.json`), and add `MACHINE_CLIENT_ID` as a Worker secret
(the service token's Client ID) with one more run of `review-deploy`.
What reaches the public log: "review built", `{"stored": true, "season": 2027, "collected_at": ...}`, "published lines: HTTP 200".
