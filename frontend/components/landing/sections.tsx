import { clsx } from "clsx";
import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import { Brand } from "@/components/brand";
import { AgentPreview } from "@/components/landing/agent-preview";
import { AmigoAnchor } from "@/components/landing/backdrop";
import { HeroStage } from "@/components/landing/hero-stage";
import { icons } from "@/components/landing/icons";
import { MatchPreview } from "@/components/landing/match-preview";
import { TiltCard } from "@/components/landing/tilt-card";
import { LinkButton } from "@/components/ui/button";
import { BRAND } from "@/lib/brand";

// Wide, fluid content column (the app itself stays narrower).
const CONTAINER = "mx-auto w-full max-w-[90rem] px-5 sm:px-8 lg:px-14";

/** Stagger index for scroll reveals. */
const stagger = (i: number) => ({ "--i": i }) as CSSProperties;

function SectionHeading({ eyebrow, title, children }: { eyebrow: string; title: ReactNode; children?: ReactNode }) {
  return (
    <div className="mx-auto max-w-3xl text-center" data-reveal>
      <p className="text-sm font-semibold tracking-wide text-[#f9a8d4] uppercase">{eyebrow}</p>
      <h2 className="mt-3 text-4xl font-semibold tracking-tight text-balance sm:text-5xl lg:text-6xl">{title}</h2>
      {children && <p className="mt-5 text-lg text-muted text-pretty sm:text-xl">{children}</p>}
    </div>
  );
}

function IconBadge({ children }: { children: ReactNode }) {
  return <span className="badge-grad grid size-11 shrink-0 place-items-center rounded-xl">{children}</span>;
}

const glow = "btn-glow h-12 px-7 text-base sm:h-14 sm:px-8 sm:text-lg";

// ------------------------------------------------------------------ hero

export function Hero() {
  return (
    <section className="relative isolate overflow-x-clip">
      <div aria-hidden className="grid-floor absolute inset-x-[-25%] top-[62%] -z-10 h-[40rem]" />
      <div className={clsx(CONTAINER, "grid min-h-[calc(100svh-4rem)] items-center gap-4 pt-10 pb-16 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-10")}>
        <div>
          <p
            data-reveal
            style={stagger(0)}
            className="glass inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-medium sm:text-sm"
          >
            <span aria-hidden className="size-2 rounded-full bg-[image:var(--grad)] shadow-[0_0_12px_#ec4899]" />
            Early access · AI job-hunt agent
          </p>
          <h1
            data-reveal
            style={stagger(1)}
            className="mt-6 text-5xl leading-[1.02] font-semibold tracking-tight text-balance sm:text-6xl lg:text-7xl xl:text-[5.6rem]"
          >
            Your AI amigo for the <span className="text-grad">job hunt</span>.
          </h1>
          <p data-reveal style={stagger(2)} className="mt-7 max-w-xl text-lg text-muted text-pretty sm:text-xl">
            {BRAND.name} finds jobs that fit, fills the forms you’ve filled a hundred times, and drafts
            answers from your real experience. It always stops and asks you before anything important.
          </p>
          <div data-reveal style={stagger(3)} className="mt-9 flex flex-wrap gap-3">
            <LinkButton href="/register" className={glow}>
              Join early access
            </LinkButton>
            <LinkButton href="#how-it-works" variant="secondary" className="glass h-12 px-7 text-base sm:h-14 sm:text-lg">
              See how it works
            </LinkButton>
          </div>
          <p data-reveal style={stagger(4)} className="mt-6 text-sm text-muted">
            You approve every application. Nothing is ever made up.
          </p>
        </div>
        <HeroStage />
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ roles marquee

const ROLES = [
  "Backend Engineer",
  "Product Designer",
  "Data Scientist",
  "DevOps Engineer",
  "Product Manager",
  "Frontend Developer",
  "ML Engineer",
  "UX Researcher",
  "Cloud Architect",
  "QA Engineer",
  "Data Analyst",
  "Mobile Developer",
];

function MarqueeRow({ items, reverse }: { items: string[]; reverse?: boolean }) {
  return (
    <div
      className="flex w-max animate-marquee gap-4"
      style={{
        animationDirection: reverse ? "reverse" : "normal",
        translate: `calc(var(--p, 0) * ${reverse ? 10 : -10}%) 0`,
      }}
    >
      {[...items, ...items].map((role, i) => (
        <span
          key={`${role}-${i}`}
          className={clsx(
            "rounded-full px-6 py-3 text-lg font-medium whitespace-nowrap sm:text-xl",
            i % 4 === 1 ? "badge-grad" : "glass",
          )}
        >
          {role}
        </span>
      ))}
    </div>
  );
}

export function RolesMarquee() {
  return (
    <section aria-label="Roles people hunt for" data-scroll="through" className="overflow-x-clip py-10 sm:py-16">
      <div aria-hidden className="[perspective:900px]">
        <div className="space-y-4 [transform:rotateX(20deg)_rotateZ(-4deg)] [mask-image:linear-gradient(90deg,transparent,black_12%,black_88%,transparent)]">
          <MarqueeRow items={ROLES} />
          <MarqueeRow items={[...ROLES].reverse()} reverse />
        </div>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ human in the loop

export function HumanInTheLoop() {
  return (
    <section className="overflow-x-clip py-20 sm:py-28">
      <div className={clsx(CONTAINER, "grid items-center gap-12 lg:grid-cols-2")}>
        <div>
          <div data-reveal>
            <p className="text-sm font-semibold tracking-wide text-[#f9a8d4] uppercase">Human in the loop</p>
            <h2 className="mt-3 text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
              It does the work. <span className="text-grad">You make the decisions.</span>
            </h2>
            <p className="mt-5 text-lg text-muted text-pretty sm:text-xl">
              When a site needs something only you should do, like creating an account, solving a CAPTCHA
              or confirming a legal statement, your amigo saves its place, tells you why, and waits. Tap
              “I’m done” and it picks up exactly where it left off.
            </p>
          </div>
          <AmigoAnchor className="mt-6 h-44 w-full sm:h-56" scale={0.95} turn={0.55} />
        </div>
        <div data-reveal>
          <TiltCard restX={6} restY={-10} max={9} className="rounded-2xl">
            <AgentPreview />
          </TiltCard>
        </div>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ problem

const PAINS = [
  {
    icon: icons.copy,
    title: "The same details, on every portal",
    body: "Name, experience, notice period, salary, retyped into every form, for every job.",
  },
  {
    icon: icons.search,
    title: "Hundreds of listings, a handful that fit",
    body: "Hours of scrolling to find the few roles that are actually worth your time.",
  },
  {
    icon: icons.robot,
    title: "Auto-apply bots that make things up",
    body: "Spray-and-pray tools invent answers and send them in your name. Recruiters notice.",
  },
];

export function PainPoints() {
  return (
    <section className="relative py-20 sm:py-28">
      <div className={CONTAINER}>
        <AmigoAnchor className="mx-auto mb-4 h-28 w-28 lg:absolute lg:top-10 lg:right-[6%] lg:mb-0 lg:h-44 lg:w-44" scale={0.9} turn={-0.4} />
        <SectionHeading eyebrow="The problem" title="Job hunting has become a second job" />
        <div className="mt-14 grid gap-6 md:grid-cols-3">
          {PAINS.map((pain, i) => (
            <div key={pain.title} data-reveal style={stagger(i)}>
              <TiltCard className="h-full rounded-3xl">
                <div className="glass h-full rounded-3xl p-7 [transform-style:preserve-3d]">
                  <div className="[transform:translateZ(34px)]">
                    <IconBadge>{pain.icon}</IconBadge>
                  </div>
                  <h3 className="mt-5 text-xl font-semibold [transform:translateZ(20px)]">{pain.title}</h3>
                  <p className="mt-2 text-muted">{pain.body}</p>
                </div>
              </TiltCard>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ 3D pipeline ring

const STAGES = [
  { icon: icons.search, title: "Search", body: "Scans supported job boards for your titles, locations and keywords." },
  { icon: icons.target, title: "Match", body: "Scores every role against your profile and explains the fit." },
  { icon: icons.form, title: "Fill", body: "Completes the standard fields from your verified profile." },
  { icon: icons.copy, title: "Attach", body: "Picks the resume that fits this job best. You can override it." },
  { icon: icons.pause, title: "Pause for you", body: "Hands over for sign-ups, CAPTCHA, MFA and legal questions." },
  { icon: icons.check, title: "Submit", body: "Only once you approve, and never twice for the same job." },
];

/** A scroll-pinned carousel: scrolling rotates six glass cards around a 3D ring. */
export function Pipeline() {
  return (
    <section id="pipeline" data-scroll="sticky" data-steps={STAGES.length} className="relative h-[340vh]">
      <div className="sticky top-0 flex h-svh flex-col items-center justify-center overflow-hidden">
        <div className={CONTAINER}>
          <SectionHeading eyebrow="The pipeline" title={<>Six steps. <span className="text-grad">Zero copy-paste.</span></>} />
        </div>
        <div className="relative mt-6 h-[300px] w-full [perspective:1400px] sm:mt-10 sm:h-[340px]">
          <div
            className="absolute top-1/2 left-1/2 size-0 [--ring-r:215px] [transform-style:preserve-3d] sm:[--ring-r:340px]"
            // Pushed back by its radius so the front card shows at true size.
            style={{
              transform: "translateZ(calc(var(--ring-r) * -1)) rotateX(-8deg) rotateY(calc(var(--p, 0) * -300deg))",
            }}
          >
            {STAGES.map((stage, i) => (
              <div
                key={stage.title}
                data-stage={i}
                className="ring-card glass absolute -top-[120px] -left-[95px] h-[240px] w-[190px] rounded-3xl p-6 opacity-55 transition-[opacity,box-shadow] duration-500 data-active:opacity-100 data-active:shadow-[0_0_80px_-12px_#ec4899] sm:-top-[130px] sm:-left-[135px] sm:h-[260px] sm:w-[270px]"
                style={{ transform: `rotateY(${i * 60}deg) translateZ(var(--ring-r))` }}
              >
                <div className="flex items-center justify-between">
                  <IconBadge>{stage.icon}</IconBadge>
                  <span className="text-4xl font-semibold text-white/15">0{i + 1}</span>
                </div>
                <h3 className="mt-5 text-xl font-semibold sm:text-2xl">{stage.title}</h3>
                <p className="mt-2 text-sm text-muted sm:text-base">{stage.body}</p>
              </div>
            ))}
          </div>
        </div>
        <ol aria-label="Pipeline steps" className="mt-8 flex gap-2">
          {STAGES.map((stage, i) => (
            <li
              key={stage.title}
              data-stage={i}
              className="h-1.5 w-7 rounded-full bg-white/15 transition-all duration-500 data-active:w-14 data-active:bg-[image:var(--grad)]"
            >
              <span className="sr-only">{stage.title}</span>
            </li>
          ))}
        </ol>
        <AmigoAnchor className="mt-4 h-24 w-24 sm:h-28 sm:w-28" scale={1} />
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ how it works

const STEPS = [
  {
    icon: icons.user,
    title: "Tell it about you, once",
    body: "Your experience, skills, education and what you’re looking for: roles, locations, salary, deal-breakers.",
  },
  {
    icon: icons.target,
    title: "It finds jobs that fit, and says why",
    body: "Every match comes with reasons and any missing requirements, so you know what you’re applying to.",
  },
  {
    icon: icons.form,
    title: "It does the repetitive work",
    body: "Fills standard fields, attaches the right resume and drafts answers using only your verified information.",
  },
  {
    icon: icons.hand,
    title: "You make the calls",
    body: "It pauses for account sign-ups, CAPTCHAs, MFA, legal questions and anything it isn’t sure about.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="relative scroll-mt-20 overflow-x-clip py-20 sm:py-28">
      <div className={CONTAINER}>
        <AmigoAnchor className="mx-auto mb-4 h-28 w-28 lg:absolute lg:top-8 lg:left-[5%] lg:mb-0 lg:h-44 lg:w-44" scale={0.9} turn={0.4} />
        <SectionHeading eyebrow="How it works" title={<>Set it up once. <span className="text-grad">Stay in control.</span></>}>
          Think of it as a friend who’s great with forms, never gets tired, and checks with you before doing
          anything that matters.
        </SectionHeading>
        <ol className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => (
            <li key={step.title} data-reveal style={stagger(i)}>
              <TiltCard className="h-full rounded-3xl">
                <div className="glass relative h-full rounded-3xl p-7 [transform-style:preserve-3d]">
                  <div className="flex items-center justify-between [transform:translateZ(36px)]">
                    <IconBadge>{step.icon}</IconBadge>
                    <span className="text-grad text-4xl font-semibold">0{i + 1}</span>
                  </div>
                  <h3 className="mt-5 text-lg font-semibold [transform:translateZ(20px)]">{step.title}</h3>
                  <p className="mt-2 text-sm text-muted">{step.body}</p>
                </div>
              </TiltCard>
            </li>
          ))}
        </ol>

        <div className="mt-28 grid items-center gap-12 lg:grid-cols-2">
          <div>
            <div data-reveal>
              <p className="text-sm font-semibold tracking-wide text-[#f9a8d4] uppercase">Explained matches</p>
              <h3 className="mt-3 text-3xl font-semibold tracking-tight sm:text-5xl">
                No black box. <span className="text-grad">Every job comes with its reasons.</span>
              </h3>
              <p className="mt-5 text-lg text-muted">
                {BRAND.name} scores each role against your profile: skills, experience, location, salary and
                your preferences. You set the minimum score and the weights. It shows exactly why a job made
                the cut and what you might be missing.
              </p>
              <ul className="mt-7 space-y-3">
                {[
                  "Duplicates and expired listings removed",
                  "Companies and industries you exclude never show up",
                  "Recommends which of your resumes fits each job, and you can override it",
                ].map((item) => (
                  <li key={item} className="flex gap-3">
                    <span className="text-success">{icons.check}</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <AmigoAnchor className="mt-6 h-40 w-full sm:h-48" scale={0.9} turn={0.55} />
          </div>
          <div data-reveal>
            <TiltCard restX={4} restY={10} className="rounded-2xl">
              <MatchPreview />
            </TiltCard>
          </div>
        </div>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ trust

const PROMISES = [
  {
    icon: icons.shield,
    title: "Only your real information",
    body: "It never invents companies, degrees, certifications, years of experience or skills.",
  },
  {
    icon: icons.pause,
    title: "Humans-only steps stay human",
    body: "CAPTCHA, MFA, email verification and account creation come to you. It never tries to bypass them.",
  },
  {
    icon: icons.check,
    title: "You approve before it submits",
    body: "Review every completed application, or allow routine ones through. It’s your choice, and you can change it any time.",
  },
  {
    icon: icons.chat,
    title: "Sensitive questions are yours",
    body: "Legal declarations, visa status and anything it’s unsure about are always asked, never guessed.",
  },
  {
    icon: icons.stop,
    title: "Stop it with one click",
    body: "Pause or stop your amigo whenever you like. It never loses its place.",
  },
  {
    icon: icons.lock,
    title: "Private by design",
    body: "Your data is used only to apply on your behalf, with daily limits you control.",
  },
];

export function Trust() {
  return (
    <section id="trust" className="relative scroll-mt-20 py-20 sm:py-28">
      <div className={CONTAINER}>
        <AmigoAnchor className="mx-auto mb-4 h-28 w-28 lg:absolute lg:top-8 lg:right-[6%] lg:mb-0 lg:h-44 lg:w-44" scale={0.9} turn={-0.4} />
        <SectionHeading eyebrow="Why you can trust it" title={<>The amigo that <span className="text-grad">never lies for you</span></>}>
          Most auto-apply tools optimise for volume. {BRAND.name} optimises for applications you’d be proud
          to have sent yourself.
        </SectionHeading>
        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {PROMISES.map((promise, i) => (
            <div
              key={promise.title}
              data-reveal
              style={stagger(i % 3)}
              className="glass group flex gap-4 rounded-3xl p-6 transition-shadow duration-300 hover:shadow-[0_0_60px_-18px_#ec4899]"
            >
              <IconBadge>{promise.icon}</IconBadge>
              <div>
                <h3 className="font-semibold">{promise.title}</h3>
                <p className="mt-1 text-sm text-muted">{promise.body}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ closing

export function FinalCta() {
  return (
    <section className="py-20 sm:py-28">
      <div className={clsx(CONTAINER, "max-w-6xl")}>
        <AmigoAnchor className="mx-auto -mb-10 h-40 w-40 sm:h-52 sm:w-52" scale={1.1} />
        <div
          data-reveal
          className="relative overflow-hidden rounded-[2rem] bg-[image:var(--grad)] px-6 py-16 text-center text-white shadow-[0_30px_120px_-30px_#ec4899] sm:px-12 sm:py-20"
        >
          <div aria-hidden className="absolute inset-0 bg-[radial-gradient(40%_80%_at_85%_0%,rgb(255_255_255/0.35),transparent)]" />
          <div aria-hidden className="absolute -bottom-24 -left-16 size-72 rounded-full bg-white/15 blur-3xl" />
          <h2 className="relative text-4xl font-semibold tracking-tight text-balance sm:text-6xl">
            Let your amigo handle the busywork.
          </h2>
          <p className="relative mx-auto mt-5 max-w-2xl text-lg opacity-90 sm:text-xl">
            Set up your profile today, and be first in line as automatic applications roll out.
          </p>
          <Link
            href="/register"
            className="relative mt-9 inline-flex h-14 items-center rounded-xl bg-white px-8 text-lg font-semibold text-[#1a1033] shadow-[0_12px_40px_-12px_rgb(26_16_51/0.6)] transition-transform hover:-translate-y-0.5 focus-visible:ring-4 focus-visible:ring-white/60 focus-visible:outline-none"
          >
            Join early access
          </Link>
        </div>
      </div>
    </section>
  );
}

export function LandingFooter() {
  return (
    <footer className="border-t border-line">
      <div className={clsx(CONTAINER, "flex flex-wrap items-center justify-between gap-4 py-8 text-sm text-muted")}>
        <div className="flex items-center gap-3">
          <Brand />
          <span>© {new Date().getFullYear()}</span>
        </div>
        <nav aria-label="Footer" className="flex gap-6">
          <Link href="/login" className="hover:text-fg">
            Sign in
          </Link>
          <Link href="/register" className="hover:text-fg">
            Create account
          </Link>
        </nav>
      </div>
    </footer>
  );
}
