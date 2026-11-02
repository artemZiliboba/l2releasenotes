import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';
const patches = defineCollection({ loader: glob({ pattern: '**/*.md', base: './src/content/patches' }), schema: z.object({ title: z.string(), date: z.coerce.date(), summary: z.string(), source_url: z.string().url(), source_id: z.string(), version: z.string().default('Essence'), categories: z.array(z.string()).default([]) }) });
export const collections = { patches };
