const DATA_URL = 'data/signs.json';
const libraryGrid = document.getElementById('library-grid');
const searchInput = document.getElementById('search-input');
const libraryCount = document.getElementById('library-count');
const loadMoreButton = document.getElementById('load-more');
const qualityFilter = document.getElementById('quality-filter');
const quizCount = document.getElementById('quiz-count');
const quizImage = document.getElementById('quiz-image');
const quizPrompt = document.getElementById('quiz-prompt');
const quizOptions = document.getElementById('quiz-options');
const quizFeedback = document.getElementById('quiz-feedback');
const nextQuestionButton = document.getElementById('next-question');
const showLibraryButton = document.getElementById('show-library');
const showQuizButton = document.getElementById('show-quiz');
const librarySection = document.getElementById('library-section');
const quizSection = document.getElementById('quiz-section');

let allSigns = [];
let currentQuestion = null;
let quizMode = 'code';
let filteredSigns = [];
let renderedCount = 0;
let imageObserver = null;

const LIBRARY_PAGE_SIZE = 24;
const RENDER_CHUNK_SIZE = 6;

function humanizeLabel(text) {
  let result = text
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/([A-Za-z])(\d)/g, '$1 $2')
    .replace(/([\d])([A-Za-z])/g, '$1 $2')
    .replace(/sign\b/gi, 'sign');
  result = result.replace(/\b([A-Z]{2,})\b/g, (match) => {
    return match.toLowerCase();
  });
  result = result.replace(/\s+/g, ' ').trim();
  return result.split(' ').map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function shuffle(array) {
  const clone = array.slice();
  for (let i = clone.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [clone[i], clone[j]] = [clone[j], clone[i]];
  }
  return clone;
}

function setActiveTab(tab) {
  showLibraryButton.classList.toggle('active', tab === 'library');
  showQuizButton.classList.toggle('active', tab === 'quiz');
  librarySection.classList.toggle('active', tab === 'library');
  quizSection.classList.toggle('active', tab === 'quiz');
}

function setupImageObserver() {
  if (!('IntersectionObserver' in window)) {
    return;
  }
  imageObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) {
        return;
      }
      const img = entry.target;
      const deferredSrc = img.getAttribute('data-src');
      if (deferredSrc && !img.getAttribute('src')) {
        img.src = deferredSrc;
      }
      imageObserver.unobserve(img);
    });
  }, {
    rootMargin: '200px 0px',
    threshold: 0.01,
  });
}

function createSignCard(sign) {
  const card = document.createElement('article');
  card.className = 'sign-card';
  const idMatch = String(sign.filename || '').match(/_(\d+)\./);
  const fallbackCode = `P${sign.page}-${idMatch ? idMatch[1] : 'UNK'}`;
  const codeLabel = sign.code || fallbackCode;
  const descLabel = sign.description || (sign.code ? `Code ${sign.code}` : 'Extracted sign (unlabeled)');

  const img = document.createElement('img');
  img.setAttribute('data-src', `signs/${sign.filename}`);
  img.removeAttribute('src');
  img.alt = `${codeLabel} ${humanizeLabel(descLabel)}`;
  img.loading = 'lazy';
  img.decoding = 'async';

  if (imageObserver) {
    imageObserver.observe(img);
  } else {
    img.src = img.getAttribute('data-src');
  }

  const title = document.createElement('h3');
  title.textContent = codeLabel;

  const description = document.createElement('p');
  description.textContent = humanizeLabel(descLabel);

  const page = document.createElement('p');
  page.textContent = `Page ${sign.page}`;
  page.style.fontSize = '0.95rem';
  page.style.color = '#6b7280';

  card.append(img, title, description, page);
  return card;
}

function updateLibraryMeta() {
  libraryCount.textContent = `${filteredSigns.length} signs available`;
  const hasMore = renderedCount < filteredSigns.length;
  loadMoreButton.style.display = hasMore ? 'inline-block' : 'none';
  if (hasMore) {
    loadMoreButton.textContent = `Load More (${renderedCount}/${filteredSigns.length})`;
  }
}

function getFilteredSigns() {
  const query = searchInput.value.trim().toLowerCase();
  const mode = qualityFilter.value;

  return allSigns
    .filter((sign) => {
      if (mode === 'ok') return sign.status === 'ok';
      if (mode === 'warning') return sign.status === 'warning';
      return true;
    })
    .filter((sign) => {
      const code = (sign.code || '').toLowerCase();
      const fallback = `p${sign.page}-${String(sign.filename || '').toLowerCase()}`;
      const description = humanizeLabel(sign.description || '').toLowerCase();
      if (!query) return true;
      return code.includes(query) || description.includes(query) || fallback.includes(query);
    })
    .sort((a, b) => {
      if ((b.confidence || 0) !== (a.confidence || 0)) {
        return (b.confidence || 0) - (a.confidence || 0);
      }
      if (a.page !== b.page) return a.page - b.page;
      return String(a.filename).localeCompare(String(b.filename));
    });
}

function appendLibraryBatch() {
  const nextCount = Math.min(renderedCount + LIBRARY_PAGE_SIZE, filteredSigns.length);
  if (nextCount <= renderedCount) {
    updateLibraryMeta();
    return;
  }

  const batch = filteredSigns.slice(renderedCount, nextCount);
  let cursor = 0;

  function renderChunk() {
    const fragment = document.createDocumentFragment();
    const chunkEnd = Math.min(cursor + RENDER_CHUNK_SIZE, batch.length);
    for (let i = cursor; i < chunkEnd; i += 1) {
      fragment.append(createSignCard(batch[i]));
    }
    libraryGrid.append(fragment);
    cursor = chunkEnd;

    if (cursor < batch.length) {
      window.requestAnimationFrame(renderChunk);
      return;
    }

    renderedCount = nextCount;
    updateLibraryMeta();
  }

  window.requestAnimationFrame(renderChunk);
}

function renderLibrary(signs) {
  filteredSigns = signs;
  renderedCount = 0;
  libraryGrid.innerHTML = '';

  if (!filteredSigns.length) {
    libraryGrid.innerHTML = '<p>No matches found.</p>';
    updateLibraryMeta();
    return;
  }

  appendLibraryBatch();
}

function applySearch() {
  renderLibrary(getFilteredSigns());
}

function getRandomQuestion() {
  if (!allSigns.length) {
    return null;
  }
  const quizPool = allSigns.filter((sign) => !!sign.code);
  if (!quizPool.length) {
    return null;
  }
  const candidate = quizPool[Math.floor(Math.random() * quizPool.length)];
  const options = new Set([candidate.code]);
  while (options.size < 4 && options.size < quizPool.length) {
    const randomSign = quizPool[Math.floor(Math.random() * quizPool.length)];
    options.add(randomSign.code);
  }
  const optionList = shuffle(Array.from(options));

  return {
    sign: candidate,
    options: optionList,
  };
}

function showQuestion() {
  currentQuestion = getRandomQuestion();
  if (!currentQuestion) {
    quizPrompt.textContent = 'No sign data available.';
    quizOptions.innerHTML = '';
    return;
  }

  quizImage.src = `signs/${currentQuestion.sign.filename}`;
  quizImage.alt = `${currentQuestion.sign.code} quiz image`;
  quizPrompt.textContent = 'What is the code for this sign?';
  quizFeedback.textContent = '';
  quizFeedback.className = 'quiz-feedback';

  quizOptions.innerHTML = '';
  currentQuestion.options.forEach((optionCode) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'option-button secondary';
    button.textContent = optionCode;
    button.addEventListener('click', () => selectOption(optionCode, button));
    quizOptions.append(button);
  });
}

function selectOption(optionCode, button) {
  if (!currentQuestion) return;
  const correct = optionCode === currentQuestion.sign.code;
  quizFeedback.textContent = correct
    ? `Correct! This is ${currentQuestion.sign.code}.`
    : `Wrong. The correct answer is ${currentQuestion.sign.code}.`;
  quizFeedback.className = `quiz-feedback ${correct ? 'correct' : 'incorrect'}`;
  Array.from(quizOptions.children).forEach((btn) => {
    btn.disabled = true;
    if (btn.textContent === currentQuestion.sign.code) {
      btn.style.borderColor = '#047857';
    }
  });
  button.style.opacity = '1';
}

function loadSigns() {
  fetch(DATA_URL)
    .then((response) => response.json())
    .then((data) => {
      allSigns = data.map((item) => ({
        ...item,
        code: item.code || '',
        description: item.description || '',
      }));

      const codedSigns = allSigns.filter((sign) => !!sign.code);
      quizCount.textContent = `${codedSigns.length} quiz-ready signs loaded`;
      renderLibrary(getFilteredSigns());
      showQuestion();
    })
    .catch((error) => {
      console.error('Unable to load sign data:', error);
      libraryGrid.innerHTML = '<p>Unable to load sign data.</p>';
      quizPrompt.textContent = 'Unable to load sign data.';
    });
}

showLibraryButton.addEventListener('click', () => setActiveTab('library'));
showQuizButton.addEventListener('click', () => setActiveTab('quiz'));
searchInput.addEventListener('input', applySearch);
qualityFilter.addEventListener('change', applySearch);
loadMoreButton.addEventListener('click', appendLibraryBatch);
nextQuestionButton.addEventListener('click', showQuestion);

setupImageObserver();
loadSigns();
