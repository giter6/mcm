% =====================================================================
% mcmthesis.cls -- a single-file LaTeX class for MCM/ICM papers
%
% Usage:
%   \documentclass{mcmthesis}
%   \contest{MCM}      % MCM (problems A/B/C) or ICM (problems D/E/F)
%   \problem{A}
%   \team{0000000}     % team control number
%   \title{...}
%   \begin{document}
%     \input{abstract}   % defines \summary{...} and \keywords{...}
%     \maketitle         % typesets the MCM/ICM Summary Sheet (page 1)
%     \input{paper_content}
%     \input{appendix}
%     \bibliographystyle{plainnat}
%     \bibliography{ref}
%   \end{document}
%
% The class is intentionally self-contained: it only uses packages that
% ship with a full TeX Live installation, so `latexmk -pdf main.tex`
% works out of the box.
% =====================================================================
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{mcmthesis}[2026/01/01 v1.0 MCM/ICM paper class]

\LoadClass[12pt,letterpaper]{article}

% ---------- page layout ----------
\RequirePackage{geometry}
\geometry{left=1in,right=1in,top=1in,bottom=1in}

% ---------- fonts: Times-like for text and math ----------
\RequirePackage{mathptmx}

% ---------- math, tables, figures ----------
\RequirePackage{amsmath,amssymb,amsthm,bm}
\RequirePackage{graphicx}
\RequirePackage{booktabs}
\RequirePackage{longtable}
\RequirePackage{multirow}
\RequirePackage{array}
\RequirePackage{enumitem}
\RequirePackage{caption}
\captionsetup{font=small,labelfont=bf,skip=6pt}
\RequirePackage[numbers,sort&compress]{natbib}

% ---------- header / footer ----------
\RequirePackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0pt}

% ---------- headings ----------
\RequirePackage{titlesec}
\titleformat{\section}{\large\bfseries}{\thesection.}{0.5em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection}{0.5em}{}
\titlespacing*{\section}{0pt}{1.2ex plus .3ex}{0.8ex plus .2ex}
\titlespacing*{\subsection}{0pt}{1ex plus .2ex}{0.6ex plus .1ex}

% ---------- hyperlinks (load late) ----------
\RequirePackage{hyperref}
\hypersetup{hidelinks}

% ---------- theorem environments ----------
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{corollary}[theorem]{Corollary}
\newtheorem{proposition}[theorem]{Proposition}
\theoremstyle{definition}
\newtheorem{definition}[theorem]{Definition}
\newtheorem{example}[theorem]{Example}
\newtheorem{remark}[theorem]{Remark}

% ---------- information used by the summary sheet ----------
\newcommand{\@team}{0000000}
\newcommand{\@contest}{MCM}
\newcommand{\@problem}{A}
\newcommand{\@mcmkeywords}{}
\newcommand{\@summary}{}
\newcommand{\team}[1]{\renewcommand{\@team}{#1}}
\newcommand{\contest}[1]{\renewcommand{\@contest}{#1}}
\newcommand{\problem}[1]{\renewcommand{\@problem}{#1}}
\newcommand{\keywords}[1]{\renewcommand{\@mcmkeywords}{#1}}
\newcommand{\summary}[1]{\renewcommand{\@summary}{#1}}

% ---------- MCM/ICM Summary Sheet (page 1) ----------
\renewcommand{\maketitle}{%
  \begin{flushright}
    {\small Team Control Number: \@team}\\[2pt]
    {\small Problem Chosen: \@problem}
  \end{flushright}%
  \vspace{-1.2em}
  \begin{center}
    {\large\bfseries \@contest{} Summary Sheet}\\[8pt]
    {\LARGE\bfseries \@title}\\[12pt]
    {\large\bfseries Summary}
  \end{center}
  \@summary
  \vspace{0.8em}

  \noindent\textbf{Keywords:} \@mcmkeywords
  \newpage
}

% ---------- small helpers used by the skeleton ----------
\newcommand{\mcmfigure}[3][htbp]{%
  % 1 = placement, 2 = file (relative to repo root), 3 = caption
  \begin{figure}[#1]
    \centering
    \includegraphics[width=0.8\linewidth]{#2}
    \caption{#3}
  \end{figure}
}
\newcommand{\mcminput}[1]{\input{#1}}

\endinput
