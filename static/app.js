const chatView = document.getElementById('chat-view');
const dashboardView = document.getElementById('dashboard-view');
const chatHistory = document.getElementById('chat-history');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const dashboardContent = document.getElementById('dashboard-content');
const resetBtn = document.getElementById('reset-btn');
const loadingText = document.getElementById('loading-text');

let currentJobId = null;
let latestReportMarkdown = "";
let followupHistory = [];
let followupBusy = false;
let activeRecognition = null;
let lastBotAnswer = "";

const voiceLangMap = {
    en: 'en-US',
    hi: 'hi-IN',
    ml: 'ml-IN'
};

// EVENT LISTENERS
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});
resetBtn.addEventListener('click', () => location.reload());

// LANGUAGE SUPPORT
const langSelector = document.getElementById('language-selector');
let currentLang = 'en';

langSelector.addEventListener('change', (e) => {
    setLanguage(e.target.value);
});

function setLanguage(lang) {
    currentLang = lang;
    const t = translations[lang];
    if (!t) return;

    // Update all elements with data-i18n
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');

        // Handle placeholders specially
        if (key.startsWith('[placeholder]')) {
            const realKey = key.replace('[placeholder]', '');
            el.placeholder = t[realKey] || realKey;
        } else {
            if (t[key]) {
                el.textContent = t[key];
            }
        }
    });

    // Update dynamic status if needed (simple check)
    if (loadingText.getAttribute('data-i18n')) {
        // let it update via the loop above
    }

    updateFollowupLanguageLabels();
}

// Initialize
setLanguage('en');

// Chip Interaction
document.querySelectorAll('.option-chip').forEach(chip => {
    chip.addEventListener('click', () => {
        const val = chip.getAttribute('data-value');
        const currentText = userInput.value;

        if (currentText) {
            userInput.value = currentText + ", " + val;
        } else {
            userInput.value = val;
        }
        userInput.focus();
    });
});

document.querySelectorAll('.custom-chip-input').forEach(input => {
    input.addEventListener('change', () => {
        const val = input.value.trim();
        if (val) {
            const currentText = userInput.value;
            if (currentText) {
                userInput.value = currentText + ", " + val;
            } else {
                userInput.value = val;
            }
            // Optional: clear input or keep it. Let's clear to indicate "moved"
            // input.value = ''; // User requested to keep data
            userInput.focus();
        }
    });

    // Also handle Enter key
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            input.blur(); // Triggers change event
        }
    });
});

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // UI: Add User Message
    addMessage(text, 'user');
    userInput.value = '';

    // UI: Transition to Dashboard view for "Live Build"
    // Ideally we might keep chatting if probing, but for MVP we assume 1-shot input
    switchToDashboard();

    // API: Start Plan
    try {
        const response = await fetch('/api/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                language: currentLang
            })
        });

        const data = await response.json();

        if (data.job_id) {
            currentJobId = data.job_id;
            startStream(currentJobId);
        } else {
            showError("Failed to start job.");
        }

    } catch (err) {
        showError("Network Error: " + err.message);
    }
}

function startStream(jobId) {
    const eventSource = new EventSource(`/api/plan/${jobId}/stream`);

    eventSource.onmessage = function (event) {
        const data = JSON.parse(event.data);
        handleStreamEvent(data, eventSource);
    };

    eventSource.onerror = function (err) {
        console.error("Stream failed", err);
        loadingText.textContent = "Connection closed. Check console/server logs.";
        loadingText.style.color = "orange";
        eventSource.close();
    };
}

let accumulatedOutput = "";

function handleStreamEvent(data, eventSource) {
    // 1. Progress Updates
    if (data.step) {
        if (data.status === 'running') {
            loadingText.textContent = `Running: ${formatStepName(data.step)}...`;
        } else if (data.status === 'completed') {
            console.log(`✅ ${formatStepName(data.step)} Completed. Output:`, data.output);
        }
    }

    // 2. Completion
    if (data.event === 'complete') {
        renderFinalReport(data.result);
        loadingText.parentElement.style.display = 'none'; // Hide loader
        eventSource.close(); // Close the EventSource
    }

    // 3. Error
    if (data.event === 'error') {
        loadingText.textContent = "Error: " + data.message;
        loadingText.style.color = "red";
        eventSource.close(); // Close stream on error
    }
}

function renderFinalReport(markdownText) {
    latestReportMarkdown = markdownText;
    followupHistory = [];
    lastBotAnswer = "";

    dashboardContent.innerHTML = ""; // Clear loader

    // Use marked.js to render
    // We wrap it in a div for styling
    const reportDiv = document.createElement('div');
    reportDiv.className = 'report-section markdown-body';
    reportDiv.innerHTML = marked.parse(markdownText);

    dashboardContent.appendChild(reportDiv);
    dashboardContent.appendChild(buildFollowupPanel());
}

function buildFollowupPanel() {
    const panel = document.createElement('div');
    panel.className = 'report-section followup-panel';
    panel.id = 'followup-panel';

    panel.innerHTML = `
        <h3 id="followup-title">Ask Follow-up Questions</h3>
        <p id="followup-subtitle" class="followup-subtitle">Use text or voice to ask questions based on this report.</p>

        <div id="followup-messages" class="followup-messages">
            <div class="followup-message followup-bot">
                You can ask follow-up questions now.
            </div>
        </div>

        <div class="followup-input-row">
            <textarea id="followup-input" class="followup-input" placeholder="Ask a question about this report..."></textarea>
            <button id="followup-mic-btn" class="followup-action-btn" type="button">Mic</button>
            <button id="followup-send-btn" class="followup-action-btn followup-send-btn" type="button">Ask</button>
            <button id="followup-speak-btn" class="followup-action-btn" type="button">Speak</button>
        </div>

        <p id="followup-status" class="followup-status"></p>
    `;

    const followupInput = panel.querySelector('#followup-input');
    const followupSendBtn = panel.querySelector('#followup-send-btn');
    const followupMicBtn = panel.querySelector('#followup-mic-btn');
    const followupSpeakBtn = panel.querySelector('#followup-speak-btn');

    followupSendBtn.addEventListener('click', askFollowupQuestion);
    followupMicBtn.addEventListener('click', toggleVoiceInput);
    followupSpeakBtn.addEventListener('click', speakLastAnswer);

    followupInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            askFollowupQuestion();
        }
    });

    updateFollowupLanguageLabels();
    return panel;
}

function updateFollowupLanguageLabels() {
    const panel = document.getElementById('followup-panel');
    if (!panel) return;

    const t = translations[currentLang] || {};

    const title = panel.querySelector('#followup-title');
    const subtitle = panel.querySelector('#followup-subtitle');
    const input = panel.querySelector('#followup-input');
    const micBtn = panel.querySelector('#followup-mic-btn');
    const sendBtn = panel.querySelector('#followup-send-btn');
    const speakBtn = panel.querySelector('#followup-speak-btn');

    if (title) title.textContent = t.followup_title || 'Ask Follow-up Questions';
    if (subtitle) subtitle.textContent = t.followup_subtitle || 'Use text or voice to ask questions based on this report.';
    if (input) input.placeholder = t.followup_placeholder || 'Ask a question about this report...';
    if (micBtn) micBtn.textContent = t.followup_mic || 'Mic';
    if (sendBtn) sendBtn.textContent = t.followup_ask || 'Ask';
    if (speakBtn) speakBtn.textContent = t.followup_speak || 'Speak';
}

function addFollowupMessage(text, sender, asMarkdown = false) {
    const messages = document.getElementById('followup-messages');
    if (!messages) return;

    const div = document.createElement('div');
    div.className = `followup-message ${sender === 'user' ? 'followup-user' : 'followup-bot'}`;

    if (asMarkdown) {
        div.innerHTML = marked.parse(text);
    } else {
        div.textContent = text;
    }

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

function setFollowupStatus(text, isError = false) {
    const status = document.getElementById('followup-status');
    if (!status) return;

    status.textContent = text || '';
    status.style.color = isError ? '#c62828' : '#666666';
}

async function askFollowupQuestion() {
    if (followupBusy) return;

    const input = document.getElementById('followup-input');
    if (!input) return;

    const question = input.value.trim();
    if (!question) return;
    if (!currentJobId || !latestReportMarkdown) {
        setFollowupStatus('Report context is not ready yet.', true);
        return;
    }

    followupBusy = true;
    input.value = '';
    addFollowupMessage(question, 'user');
    followupHistory.push({ role: 'user', content: question });
    setFollowupStatus((translations[currentLang] || {}).followup_wait || 'Getting answer...');

    const sendBtn = document.getElementById('followup-send-btn');
    const micBtn = document.getElementById('followup-mic-btn');
    if (sendBtn) sendBtn.disabled = true;
    if (micBtn) micBtn.disabled = true;

    try {
        const response = await fetch('/api/followup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_id: currentJobId,
                question,
                language: currentLang,
                history: followupHistory.slice(-12)
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }

        const answer = (data.answer || '').trim();
        if (!answer) {
            throw new Error('Empty follow-up answer from server.');
        }

        lastBotAnswer = answer;
        followupHistory.push({ role: 'assistant', content: answer });
        addFollowupMessage(answer, 'bot', true);
        setFollowupStatus('');
    } catch (err) {
        const msg = 'Follow-up failed: ' + err.message;
        addFollowupMessage(msg, 'bot');
        setFollowupStatus(msg, true);
    } finally {
        followupBusy = false;
        if (sendBtn) sendBtn.disabled = false;
        if (micBtn) micBtn.disabled = false;
    }
}

function toggleVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const micBtn = document.getElementById('followup-mic-btn');
    const input = document.getElementById('followup-input');

    if (!input) return;

    if (!SpeechRecognition) {
        setFollowupStatus('Speech recognition is not supported in this browser.', true);
        return;
    }

    if (activeRecognition) {
        activeRecognition.stop();
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = voiceLangMap[currentLang] || 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
        activeRecognition = recognition;
        if (micBtn) micBtn.textContent = 'Stop';
        setFollowupStatus((translations[currentLang] || {}).followup_listening || 'Listening...');
    };

    recognition.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript || '';
        const current = input.value.trim();
        input.value = current ? `${current} ${transcript}` : transcript;
        input.focus();
    };

    recognition.onerror = (event) => {
        setFollowupStatus(`Voice input error: ${event.error}`, true);
    };

    recognition.onend = () => {
        activeRecognition = null;
        if (micBtn) micBtn.textContent = (translations[currentLang] || {}).followup_mic || 'Mic';
        if (!followupBusy) setFollowupStatus('');
    };

    recognition.start();
}

function stripMarkdown(text) {
    return text
        .replace(/```[\s\S]*?```/g, ' ')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\*([^*]+)\*/g, '$1')
        .replace(/\[(.*?)\]\((.*?)\)/g, '$1')
        .replace(/^#+\s+/gm, ' ')
        .replace(/\n+/g, ' ')
        .trim();
}

function speakLastAnswer() {
    if (!window.speechSynthesis) {
        setFollowupStatus('Speech synthesis is not supported in this browser.', true);
        return;
    }

    if (!lastBotAnswer) {
        setFollowupStatus('No answer available to speak yet.', true);
        return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(stripMarkdown(lastBotAnswer));
    utterance.lang = voiceLangMap[currentLang] || 'en-US';
    window.speechSynthesis.speak(utterance);
}

// HELPERS
function addMessage(text, sender) {
    const div = document.createElement('div');
    div.className = `message ${sender}-message`;
    div.textContent = text;
    chatHistory.appendChild(div);
    // Scroll window to bottom since we now use page scrolling
    window.scrollTo(0, document.body.scrollHeight);
}

function switchToDashboard() {
    chatView.classList.add('hidden');
    dashboardView.classList.remove('hidden');
}

function formatStepName(step) {
    return step.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function showError(msg) {
    console.error("App Error:", msg);
    alert("Error: " + msg);
    // location.reload(); // Stop reloading to debug
    loadingText.textContent = msg;
    loadingText.style.color = 'red';
}
