export interface Source {
  id: string;
  title: string;
  url: string;
  version: string;
  checkedAt: string;
}
export interface Curriculum {
  id: string;
  title: string;
  goal: string;
  dependsOn: string[];
}
export interface Profile {
  schemaVersion: 1;
  id: string;
  title: string;
  technology: string;
  version: string;
  goal: string;
  audience: string;
  officialHosts: string[];
  sources: Source[];
  curriculum: Curriculum[];
}
export interface Note {
  id: string;
  target: string;
  side: "left" | "right";
  title: string;
  body: string;
}
export interface Slide {
  file: string;
  title: string;
  notes: Note[];
}
export interface Explanation {
  title: string;
  body: string;
  code: string;
  output: string;
}
export interface Lesson {
  schemaVersion: 1;
  id: string;
  title: string;
  goal: string;
  prerequisites: string[];
  explanation: Explanation[];
  exercise: { prompt: string; answer: string };
  sources: string[];
  slides: Slide[];
}
export interface Course {
  profile: Profile;
  lessons: { lesson: Lesson; deckDir: string }[];
}
