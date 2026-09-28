# Author biographies — to fill in before IEEE Access submission

IEEE Access requires a **short biography for every author**, placed after the
references (and/or entered in the submission system). Each biography is typically
100–200 words and states the author's current position, education, research
interests, and IEEE membership (if any). **A photograph is optional** (needed
only for the HTML version, and only if you choose to supply one).

> **Do not guess.** The facts below are the only ones confirmed for this project;
> everything tagged `TODO` must be filled with real, verifiable details by the
> authors. Do not invent degrees, positions, dates, or memberships.

---

## Qiulong Lin  ✅ 已填（2026-09-28，作者确认）

- Current position / affiliation: with Yango University, Fuzhou, China; also
  affiliated with Sogang University, Seoul 04107, Republic of Korea.
- Degrees and institutions: **M.S. degree from Sogang University, Seoul,
  Republic of Korea** （作者原话"学历是硕士，韩国西江大学就读"；按"已获硕士"处理。
  若实为在读未毕业，须改 wording 为 "is pursuing the M.S. degree"）。
- Research interests: Web/API security, vulnerability discovery, metamorphic
  testing （由论文主题推导，非编造）。
- IEEE membership / grade: 未提供 → 简介中**省略**该句（不编造）。
- 已插入 `main.tex` 的 `\IEEEbiographynophoto` 环境（在 `\bibliography{refs}` 之后）。

## Nanlei Chen

- Current position / affiliation: **TODO** (known: Sogang University, Seoul,
  Republic of Korea — confirm title; corresponding author).
- Degrees and institutions: **TODO**.
- Research interests: **TODO**.
- IEEE membership / grade: **TODO**.

---

### Ready-to-paste skeleton (fill the TODO brackets)

```latex
\begin{IEEEbiographynophoto}{Qiulong Lin}
[TODO]. His research interests include [TODO]. He is a [TODO: IEEE grade / not a member].
\end{IEEEbiographynophoto}

\begin{IEEEbiographynophoto}{Nanlei Chen}
[TODO]. His research interests include [TODO]. He is a [TODO: IEEE grade / not a member].
\end{IEEEbiographynophoto}
```

> `IEEEbiographynophoto` omits the photo box; switch to `IEEEbiography` if you
> supply photos. These two blocks go **after** `\bibliography{refs}` in
> `main.tex`. They are deliberately left out of the committed manuscript until
> the real details are known.
