# Minting a Zenodo DOI for the JISA artifact

A Zenodo DOI gives the artifact a permanent, citable, versioned archive that is
independent of GitHub. Zenodo integrates with GitHub: once `.zenodo.json` is
present at the root of a *tagged* commit and you create a GitHub Release for
that tag, Zenodo automatically mints a DOI.

> Status: `.zenodo.json` is already written at the repository root. The DOI is
> **not** minted yet — that step needs your Zenodo/GitHub accounts (it cannot
> be done from this environment).

## Steps

1. **Account.** Sign up / log in at <https://zenodo.org> (ORCID login is fine;
   the paper already states the authors have no ORCID, so a plain account is OK).

2. **Link GitHub.** In Zenodo: *Account → GitHub* (top-right avatar → Settings →
   GitHub). Click **Authorize** and grant Zenodo access to your repositories.
   Toggle on the `ubfbuz3/JISA` repository so Zenodo watches it.

3. **Make the `.zenodo.json` part of the release tag.**
   The artifact tag is currently `artifact-v1` at commit `ec27917`, which does
   **not** yet contain `.zenodo.json`. To get Zenodo to pick up the metadata, the
   tagged commit must include `.zenodo.json`. Two clean options:
   - **Recommended:** keep `artifact-v1` as the canonical name. After committing
     `.zenodo.json` locally, move the `artifact-v1` tag to the new commit and
     push the tag (`git tag -f artifact-v1 <new> && git push -f origin artifact-v1`).
     This preserves the tag name referenced by the paper and the Data-availability
     statement. *(Matches the project's existing "re-anchor artifact-v1" convention.)*
   - **Alternative:** cut a fresh tag, e.g. `artifact-v1-zenodo`, release that, and
     update the paper's text to cite the new tag.

4. **Create the GitHub Release.** On GitHub, go to the repo → *Releases → Draft a
   new release*, choose the tag from step 3, add a short title/description, and
   publish. Zenodo will detect it within a minute or two and create a deposition.

5. **Publish on Zenodo.** Zenodo emails you a link to the new deposition under
   *Uploads*. Open it, verify the pre-filled metadata (title, authors, licence,
   keywords — all come from `.zenodo.json`), add a one-line description if you
   like, then click **Publish**. Zenodo assigns a DOI of the form
   `10.5281/zenodo.XXXXXXX`.

6. **Cite it.** Paste the DOI into the paper's Data-availability statement
   (see `SUBMISSION_CHECKLIST.md` → "Data Availability precise wording") on the
   clearly marked `TODO` line, then re-commit. The GitHub `artifact-v1` tag and
   the Zenodo `10.5281/zenodo.XXXXXXX` should both be referenced.

## Notes

- **Licence** is set to `cc-by-4.0` in `.zenodo.json`. If you prefer `MIT` or
  `CC0`, edit the `"license"` field before publishing (Zenodo also lets you
  change it in the deposition form before you hit Publish).
- **Do not** put a placeholder/fake DOI in the paper. Leave the `TODO` line until
  the real DOI exists.
- The GitHub repo already ships everything `reproduce.sh` / `verify_artifact.sh`
  need; Zenodo simply archives a frozen copy of the tagged tree.
