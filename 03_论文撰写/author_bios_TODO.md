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

## Nanlei Chen  ✅ 已填（2026-09-28，作者确认）

- Current position / affiliation: with Yango University, Fuzhou 350015, China
  （阳光学院在职）; and Sogang University, Seoul 04107, Republic of Korea（在读）。
- Degrees and institutions: **currently pursuing the M.S. degree at Sogang
  University**（作者原话"西江大学在读，尚未毕业"；**在读未毕业**，故用
  "is currently pursuing"，不用 "received"）。
- Research interests: Web/API security and authorization testing（由论文主题推导）。
- IEEE membership / grade: 未提供 → 简介中**省略**该句（不编造）。
- 通讯作者（已见 `main.tex` 作者块脚注）。
- 已插入 `main.tex` 的 `\IEEEbiographynophoto` 环境（在 Lin 之后）。

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
