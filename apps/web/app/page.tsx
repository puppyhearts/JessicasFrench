"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Choice = { label: string; text: string };
type Word = { text: string; start: number; end: number };
type Occurrence = { website: string; group_label: string; question_number: number; source_page: number | null; source_exercise: string | null };
type Audio = { asset_id: string; start_seconds: number | null; end_seconds: number | null; duration_seconds: number };
type Question = {
  id: string; collection: string; group_label: string; question_number: number; display_label: string;
  section: string; level: string | null; difficulty_rank: number; prompt: string | null; instructions: string | null;
  correct_answer: string | null; transcript: string | null; transcript_words: Word[]; choices: Choice[];
  occurrences: Occurrence[]; audio: Audio | null; has_image: boolean; image_url?: string | null;
};
type Collection = { slug: string; name: string; question_count: number; published_count: number };
type Attempt = { selected: string; correct: boolean };
type AttemptMap = Record<string, Attempt>;

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const AUDIO_BASE = process.env.NEXT_PUBLIC_AUDIO_BASE_URL;
const STORAGE_KEY = "french-audiopractice-attempts-v1";

async function fetchCollections(): Promise<Collection[]> {
  try {
    const response = await fetch(`${API}/api/collections`);
    if (response.ok) return response.json();
  } catch {}
  return fetch("catalog/collections.json").then((response) => response.json());
}

async function fetchQuestions(collection: string, section?: string): Promise<Question[]> {
  try {
    const params = new URLSearchParams();
    if (collection) params.set("collection", collection);
    if (section) params.set("section", section);
    const response = await fetch(`${API}/api/catalog/questions?${params}`);
    if (response.ok) return response.json();
  } catch {}
  const questions: Question[] = await fetch("catalog/questions.json").then((response) => response.json());
  return questions.filter((item) => (!collection || item.collection === collection) && (!section || item.section === section));
}

export default function PracticePage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [availableQuestions, setAvailableQuestions] = useState<Question[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [collection, setCollection] = useState("");
  const [section, setSection] = useState("listening");
  const [active, setActive] = useState(0);
  const [attempts, setAttempts] = useState<AttemptMap>({});
  const [speed, setSpeed] = useState(1);
  const [currentTime, setCurrentTime] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);
  const question = questions[active];
  const selected = question ? attempts[question.id]?.selected ?? null : null;

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved) setAttempts(JSON.parse(saved));
    fetchCollections().then(setCollections).catch(() => setCollections([]));
  }, []);

  useEffect(() => {
    fetchQuestions(collection).then(setAvailableQuestions).catch(() => setAvailableQuestions([]));
  }, [collection]);

  useEffect(() => {
    fetchQuestions(collection, section)
      .then((data: Question[]) => {
        setQuestions(data.sort((a, b) => a.difficulty_rank - b.difficulty_rank || a.collection.localeCompare(b.collection) || a.group_label.localeCompare(b.group_label) || a.question_number - b.question_number));
        setActive(0);
      })
      .catch(() => setQuestions([]));
  }, [collection, section]);

  useEffect(() => {
    if (!audioRef.current || !question) return;
    const start = question.audio?.start_seconds ?? 0;
    audioRef.current.currentTime = start;
    audioRef.current.playbackRate = speed;
    setCurrentTime(start);
  }, [question, speed]);

  const sectionCounts = useMemo(() => availableQuestions.reduce<Record<string, number>>((counts, item) => {
    counts[item.section] = (counts[item.section] ?? 0) + 1;
    return counts;
  }, {}), [availableQuestions]);
  const tally = useMemo(() => {
    const records = Object.values(attempts);
    const correct = records.filter((item) => item.correct).length;
    return { attempted: records.length, correct, score: records.length ? Math.round(correct / records.length * 100) : 0 };
  }, [attempts]);
  const groupedQuestions = useMemo(() => {
    const groups: { key: string; label: string; items: { question: Question; index: number; practiceNumber: number }[] }[] = [];
    let currentRank = -1;
    let chunk = 0;
    questions.forEach((item, index) => {
      if (item.difficulty_rank !== currentRank) {
        currentRank = item.difficulty_rank;
        chunk = 0;
      }
      if (!groups.length || groups[groups.length - 1].key !== `${currentRank}-${chunk}` || groups[groups.length - 1].items.length === 20) {
        if (groups.length && groups[groups.length - 1].items.length === 20) chunk += 1;
        groups.push({ key: `${currentRank}-${chunk}`, label: `Difficulty ${currentRank} · ${chunk * 20 + 1}-${chunk * 20 + 20}`, items: [] });
      }
      groups[groups.length - 1].items.push({ question: item, index, practiceNumber: chunk * 20 + groups[groups.length - 1].items.length + 1 });
    });
    return groups;
  }, [questions]);

  async function answer(label: string) {
    if (!question || selected) return;
    const updated = { ...attempts, [question.id]: { selected: label, correct: label === question.correct_answer } };
    setAttempts(updated);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    try {
      await fetch(`${API}/api/catalog/questions/${question.id}/attempts`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ selected_answer: label }),
      });
    } catch {}
  }

  function reset() {
    setAttempts({});
    window.localStorage.removeItem(STORAGE_KEY);
  }

  function constrainAudio() {
    if (!audioRef.current) return;
    setCurrentTime(audioRef.current.currentTime);
    if (question?.audio?.end_seconds != null && audioRef.current.currentTime >= question.audio.end_seconds) audioRef.current.pause();
  }

  return <main className="shell">
    <aside className="panel transcript">
      <header><div><strong>◉ Transcript AI</strong><small>{question?.display_label ?? "Question"}</small></div><span className="tag">{section === "listening" ? "CO" : section.toUpperCase()}</span></header>
      <div className="transcript-body">
        {question?.transcript_words?.length
          ? <p className="timed-transcript">{question.transcript_words.map((word, index) => <span className={currentTime >= word.start && currentTime < word.end ? "spoken" : ""} key={`${word.start}-${index}`}>{word.text} </span>)}</p>
          : question?.transcript ? <p>{question.transcript}</p>
          : <><p>Transcript unavailable for this imported source.</p><p className="muted">Run <code>npm run transcribe-catalog</code> to generate synchronized local transcripts.</p></>}
      </div>
    </aside>

    <section className="center">
      <header className="panel topbar">
        <div><strong>{question?.display_label ?? "No question"} — {section.toUpperCase()}</strong><small>{question?.group_label ?? "Generated local catalog"}</small></div>
        <div className="topbar-actions"><span className="difficulty">Difficulty {question?.difficulty_rank ?? "—"}</span><select value={collection} onChange={(event) => setCollection(event.target.value)}>
          <option value="">All collections</option>{collections.map((item) => <option value={item.slug} key={item.slug}>{item.name} ({item.published_count})</option>)}
        </select></div>
      </header>
      <section className="panel question-card">
        <div className="reference"><span>RÉFÉRENCE</span>{(question?.occurrences ?? []).map((item, index) =>
          <strong key={`${item.website}-${item.group_label}-${index}`}>{item.website} · {item.group_label} · Question {item.question_number}</strong>
        )}{!question && <strong>No publishable questions match the current filters.</strong>}</div>
        {!question && <div className="empty-state">No reviewed questions are available for this section and collection.</div>}
        {question?.audio && <><audio ref={audioRef} controls src={AUDIO_BASE ? `${AUDIO_BASE}/${question.audio.asset_id}.mp3` : `${API}/api/catalog/audio/${question.audio.asset_id}`} onTimeUpdate={constrainAudio} />
          <div className="speed">{[0.5, 0.75, 1, 1.25, 1.5].map((value) => <button className={speed === value ? "active" : ""} onClick={() => setSpeed(value)} key={value}>{value}x</button>)}</div></>}
        <div className="instruction">{question?.instructions || "Écoutez l'extrait ou lisez la question. Choisissez la bonne réponse."}</div>
        <h1>{question?.prompt || "Choose a collection or adjust the filters."}</h1>
        {question?.has_image && <img className="question-image" src={question.image_url ?? `${API}/api/catalog/images/${question.id}`} alt={`Source page for ${question.display_label}`} />}
        <div className="answers">{(question?.choices ?? []).map((choice) => {
          const correct = selected && choice.label === question.correct_answer;
          const wrong = selected === choice.label && choice.label !== question.correct_answer;
          return <button className={`answer ${correct ? "correct" : ""} ${wrong ? "wrong" : ""}`} key={choice.label} onClick={() => answer(choice.label)}><b>{choice.label}</b><span>{choice.text}</span></button>;
        })}</div>
        {selected && <p className={`feedback ${selected === question?.correct_answer ? "good" : "bad"}`}>{selected === question?.correct_answer ? "Bonne réponse." : `Réponse incorrecte. La bonne réponse est ${question?.correct_answer}.`}</p>}
      </section>
    </section>

    <aside className="panel navigator">
      <header><div><strong>Questions</strong><small>{questions.length} questions disponibles</small></div></header>
      <div className="score"><strong>{tally.correct}/{tally.attempted}</strong><span>{tally.score}% score</span><button onClick={reset}>Reset</button></div>
      <div className="filters">{[["listening", "CO"], ["grammar", "Grammar"], ["reading", "Reading"]].map(([value, label]) =>
        <button key={label} className={value === section ? "active" : ""} onClick={() => setSection(value)}>{label} ({sectionCounts[value] ?? 0})</button>
      )}</div>
      <div className="navigator-scroll">{groupedQuestions.map((group) => <section className="question-group" key={group.key}><h2>{group.label}</h2><div className="grid">
        {group.items.map(({ question: item, index, practiceNumber }) => {
          const attempt = attempts[item.id];
          return <button className={`${index === active ? "active" : ""} ${attempt?.correct ? "done-correct" : attempt ? "done-wrong" : ""}`} key={item.id} onClick={() => setActive(index)}>Q{practiceNumber}<small>{item.level ?? `D${item.difficulty_rank}`}</small></button>;
        })}
      </div></section>)}</div>
      <p className="disclaimer">Educational practice project. Not associated with the original publishers or test providers.</p>
    </aside>
  </main>;
}
