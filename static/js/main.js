(() => {
    "use strict";
    const screenEl = document.getElementById("term-screen");
    const inputEl  = document.getElementById("term-input");

    const INITIAL_HEADER_HTML =
        document.querySelector(".ascii-banner").outerHTML +
        document.querySelector(".sys-info").outerHTML;

    let isStateful = true;
    let variables  = {};

    const inputHistory = [];
    let histIdx = -1;
    let tabCtx  = null;
    let referenceCache = null;

    const PAGE_SIZE = 30;

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, c => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;",
            '"': "&quot;", "'": "&#39;",
        }[c]));
    }

    function append(text, cls = "") {
        const line = document.createElement("div");
        line.className = "term-line " + cls;
        line.textContent = text;
        screenEl.appendChild(line);
        screenEl.scrollTop = screenEl.scrollHeight;
    }

    let pagerActive = false;

    function appendLines(lines, cls = "output") {
        return new Promise(resolve => {
            if (pagerActive) {
                lines.forEach(l => append(l, cls));
                resolve();
                return;
            }
            if (lines.length <= PAGE_SIZE) {
                lines.forEach(l => append(l, cls));
                resolve();
                return;
            }

            pagerActive = true;
            inputEl.disabled = true;

            const queue = lines.slice();
            const slice = queue.splice(0, PAGE_SIZE);
            slice.forEach(l => append(l, cls));
            showMorePrompt(queue, cls, resolve);
        });
    }

    function showMorePrompt(queue, cls, resolve) {
        const more = document.createElement("div");
        more.className = "term-line more-prompt";
        more.textContent = "-- More -- [Enter/Space: далее, Q: выход]";
        screenEl.appendChild(more);
        screenEl.scrollTop = screenEl.scrollHeight;

        const handler = (e) => {
            if (!["Enter", " ", "q", "Q"].includes(e.key)) return;
            e.preventDefault();
            e.stopPropagation();
            more.remove();
            document.removeEventListener("keydown", handler, true);

            if (e.key === "q" || e.key === "Q" || queue.length === 0) {
                pagerActive = false;
                inputEl.disabled = false;
                inputEl.focus();
                resolve();
                return;
            }

            const slice = queue.splice(0, PAGE_SIZE);
            slice.forEach(l => append(l, cls));
            if (queue.length > 0) {
                showMorePrompt(queue, cls, resolve);
            } else {
                pagerActive = false;
                inputEl.disabled = false;
                inputEl.focus();
                resolve();
            }
        };
        document.addEventListener("keydown", handler, true);
    }

    function asciiBox(title, lines, width = 62) {
        const top = "╔" + "═".repeat(width - 2) + "╗";
        const bot = "╚" + "═".repeat(width - 2) + "╝";
        const sep = "╠" + "═".repeat(width - 2) + "╣";
        const pad = s => "║ " + String(s).padEnd(width - 4) + " ║";
        const out = [top, pad(title), sep];
        for (const l of lines) {
            if (l === null) out.push(sep);
            else out.push(pad(l));
        }
        out.push(bot);
        return out;
    }

    function renderVariables(vars) {
        const ul = document.getElementById("var-list");
        const keys = Object.keys(vars || {});
        if (keys.length === 0) {
            ul.innerHTML = '<li class="empty">&lt;пусто&gt;</li>';
            return;
        }
        ul.innerHTML = keys.map(k =>
            `<li><strong>${escapeHtml(k)}</strong> = ` +
            `<span class="val">${escapeHtml(vars[k])}</span></li>`
        ).join("");
    }

    function renderHistory(hist) {
        const ul = document.getElementById("hist-list");
        if (!hist || hist.length === 0) {
            ul.innerHTML = '<li class="empty">&lt;пусто&gt;</li>';
            return;
        }
        ul.innerHTML = hist.map((h, i) =>
            `<li><span class="idx">${i + 1}.</span> ` +
            `<code>${escapeHtml(h.expr)}</code></li>`
        ).join("");
    }

    function formatHelp() {
        return asciiBox("MATRIX CALCULATOR — КРАТКАЯ СПРАВКА", [
            "ОПЕРАТОРЫ",
            "  +   сложение              A + B",
            "  -   вычитание             A - B",
            "  *   скалярное умножение   A * 2",
            "  /   деление на скаляр     A / 2",
            "  @   матричное умножение   A @ B",
            "  **  возведение в степень  A ** 3",
            null,
            "ФУНКЦИИ",
            "  det(A)         inv(A)        rank(A)",
            "  trace(A)       transpose(A)  solve(A, b)",
            null,
            "СВОЙСТВА",
            "  A.T   A.det   A.inv   A.rank   A.trace",
            "  A.rows   A.cols   A.shape   A.is_square",
            null,
            "Введите :examples — полный справочник с примерами.",
            "Введите :commands — список всех команд.",
        ]);
    }

    async function formatExamples() {
        const ref = await loadReference();
        const out = [];
        for (const cat of ref.categories) {
            out.push("");
            out.push("[ " + cat.title.toUpperCase() + " ]");
            out.push("");
            for (const item of cat.items) {
                out.push("  " + item.expr.replace(/\n/g, "\n    "));
                out.push("    -> " + item.desc);
                out.push("");
            }
        }
        return out;
    }

    async function formatCommands() {
        const ref = await loadReference();
        const lines = ref.commands.map(c => {
            const key = c.key ? "[" + c.key + "]" : "       ";
            return key.padEnd(7) + " " + c.cmd.padEnd(20) + " — " + c.desc;
        });
        return asciiBox("КОМАНДЫ", lines, 66);
    }

    async function loadReference() {
        if (referenceCache) return referenceCache;
        const resp = await fetch("/api/reference");
        referenceCache = await resp.json();
        return referenceCache;
    }

    async function runCommand(text) {
        append(text, "input");
        const parts = text.trim().split(/\s+/);
        const cmd = parts[0].toLowerCase();

        switch (cmd) {
            case ":help":
                await appendLines(formatHelp(), "output");
                break;

            case ":examples":
                await appendLines(await formatExamples(), "output");
                break;

            case ":commands":
                await appendLines(await formatCommands(), "output");
                break;

            case ":clear":
                screenEl.innerHTML = INITIAL_HEADER_HTML;
                break;

            case ":reset": {
                await fetch("/reset", { method: "POST" });
                variables = {};
                renderVariables({});
                renderHistory([]);
                append("Сброс выполнен.", "info");
                break;
            }

            case ":stateful":
                isStateful = !isStateful;
                append(
                    "Сохранение переменных: " + (isStateful ? "ВКЛ" : "ВЫКЛ"),
                    "info"
                );
                break;

            case ":vars": {
                const names = Object.keys(variables);
                if (names.length === 0) {
                    append("Переменных нет.", "info");
                } else {
                    append("Переменные:", "info");
                    for (const n of names) {
                        await appendLines([n + " = " + variables[n]], "output");
                    }
                }
                break;
            }

            case ":history": {
                const items = [];
                screenEl.querySelectorAll(".term-line.input").forEach(el => {
                    items.push(el.textContent.trim());
                });
                if (items.length === 0) append("История пуста.", "info");
                else {
                    append("История команд:", "info");
                    await appendLines(items, "output");
                }
                break;
            }

            default:
                append("Неизвестная команда: " + cmd, "error");
        }
    }

    async function execute(text) {
        if (!text) return;

        if (text.startsWith(":")) return runCommand(text);

        append(text, "input");

        try {
            const resp = await fetch("/calculate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ expression: text, stateful: isStateful }),
            });
            const rawText = await resp.text();
            let data;
            try {
                data = JSON.parse(rawText);
            } catch (e) {
                throw new Error(
                    "Критическая ошибка сервера. Проверьте консоль Python."
                );
            }

            if (!data.ok) {
                append(data.error, "error");
                return;
            }

            await appendLines(data.result.pretty.split("\n"), "output");

            if (data.variables) {
                variables = data.variables;
                renderVariables(variables);
            }
            if (data.history) renderHistory(data.history);
        } catch (err) {
            append(err.message, "error");
        }
    }

    inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Tab") {
            e.preventDefault();
            completeTab(e.shiftKey);
            return;
        }
        tabCtx = null;

        if (e.key === "ArrowUp") {
            e.preventDefault();
            if (inputHistory.length === 0) return;
            if (histIdx < 0) histIdx = inputHistory.length;
            histIdx = Math.max(0, histIdx - 1);
            inputEl.value = inputHistory[histIdx];
            return;
        }
        if (e.key === "ArrowDown") {
            e.preventDefault();
            if (histIdx < 0) return;
            histIdx = Math.min(inputHistory.length, histIdx + 1);
            inputEl.value = histIdx === inputHistory.length
                          ? "" : inputHistory[histIdx];
            return;
        }

        if (e.key === "Enter") {
            const val = inputEl.value.trim();
            inputEl.value = "";
            if (val) inputHistory.push(val);
            histIdx = -1;
            execute(val);
            return;
        }

        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "l") {
            e.preventDefault();
            execute(":clear");
        }
    });

    document.addEventListener("keydown", (e) => {
        if (pagerActive) return;
        if (e.key === "F1") { e.preventDefault(); execute(":help"); }
        if (e.key === "F2") { e.preventDefault(); execute(":examples"); }
        if (e.key === "F3") { e.preventDefault(); execute(":commands"); }
        if (e.key === "F5") { e.preventDefault(); execute(":reset"); }
        if (e.key === "Escape") {
            e.preventDefault();
            execute(":clear");
        }
    });

    document.querySelector(".terminal-main")
        .addEventListener("click", () => {
            if (!pagerActive && !inputEl.disabled) inputEl.focus();
        });
})();