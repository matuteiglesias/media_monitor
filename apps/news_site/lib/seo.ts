import type { Metadata } from "next";
import { EDITORIAL_IDENTITY } from "@/lib/editorial_identity";
import { PUBLIC_IDENTITY } from "@/lib/public_identity";

export function canonicalUrl(pathname: string) {
  return new URL(pathname, PUBLIC_IDENTITY.public_outlet_url).toString();
}

export function personJsonLd() {
  const editor = EDITORIAL_IDENTITY.editor;
  return {
    "@context": "https://schema.org",
    "@type": "Person",
    "@id": `${canonicalUrl(EDITORIAL_IDENTITY.routes.author)}#person`,
    name: editor.name,
    jobTitle: "Economista y editor",
    description: editor.bio_short,
    url: canonicalUrl(EDITORIAL_IDENTITY.routes.author),
    sameAs: editor.same_as,
    knowsAbout: editor.expertise,
    homeLocation: { "@type": "Place", name: editor.location },
  };
}

export function authorMetadata(): Metadata {
  const editor = EDITORIAL_IDENTITY.editor;
  const title = `${editor.name} — economista y editor | ${PUBLIC_IDENTITY.outlet_name}`;
  const description = `${editor.bio_short} Áreas: ${editor.expertise.slice(0, 4).join(", ")}.`;
  return {
    title,
    description,
    alternates: { canonical: EDITORIAL_IDENTITY.routes.author },
    openGraph: {
      type: "profile",
      title,
      description,
      url: EDITORIAL_IDENTITY.routes.author,
      siteName: PUBLIC_IDENTITY.outlet_name,
      locale: "es_AR",
    },
  };
}

export function articleMetadata(article: any): Metadata {
  const pathname = `/articles/${article.slug}`;
  const title = `${article.title} | ${PUBLIC_IDENTITY.outlet_name}`;
  return {
    title,
    description: article.summary,
    authors: [{ name: EDITORIAL_IDENTITY.editor.name, url: EDITORIAL_IDENTITY.routes.author }],
    alternates: { canonical: pathname },
    openGraph: {
      type: "article",
      title,
      description: article.summary,
      url: pathname,
      siteName: PUBLIC_IDENTITY.outlet_name,
      locale: "es_AR",
      publishedTime: article.published_at,
      modifiedTime: article.updated_at,
      authors: [canonicalUrl(EDITORIAL_IDENTITY.routes.author)],
      tags: [article.topic],
    },
  };
}

export function articleJsonLd(article: any) {
  const articleUrl = canonicalUrl(`/articles/${article.slug}`);
  const personId = `${canonicalUrl(EDITORIAL_IDENTITY.routes.author)}#person`;
  return {
    "@context": "https://schema.org",
    "@type": "Article",
    "@id": `${articleUrl}#article`,
    headline: article.title,
    description: article.summary,
    articleSection: article.topic,
    datePublished: article.published_at,
    dateModified: article.updated_at,
    mainEntityOfPage: articleUrl,
    author: { "@type": "Person", "@id": personId, name: EDITORIAL_IDENTITY.editor.name },
    publisher: {
      "@type": "Organization",
      name: PUBLIC_IDENTITY.outlet_name,
      url: PUBLIC_IDENTITY.public_outlet_url,
    },
    citation: article.citations.map((citation: any) => citation.url),
  };
}

export function serializeJsonLd(value: unknown) {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}
