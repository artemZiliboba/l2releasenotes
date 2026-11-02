import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
export async function GET(context){const patches=(await getCollection('patches')).sort((a,b)=>b.data.date-a.data.date);return rss({title:'L2 KR — русские патчноуты',description:'Переводы обновлений Lineage 2 Essence',site:context.site,items:patches.map(p=>({title:p.data.title,pubDate:p.data.date,description:p.data.summary,link:'patches/'+p.id+'/'}))});}
