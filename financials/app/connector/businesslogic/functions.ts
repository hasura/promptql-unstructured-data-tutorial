import { Pool } from "pg";
import OpenAI from "openai";

// Initialize global clients
const pool = new Pool({
  connectionString:
    process.env.DATABASE_URL ||
    "postgresql://postgres:postgres@localhost:5432/dev",
});

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

/**
 * Configurable topics for analyzing company growth trends
 * Add or modify topics here to adjust the analysis focus
 */
const GROWTH_ANALYSIS_TOPICS = [
  "revenue growth",
  "market expansion",
  "new products",
  "profitability",
  "customer acquisition",
  "operational efficiency",
  "market share",
  "innovation pipeline",
];

interface GrowthAnalysis {
  stockSymbol: string;
  startDate: string;
  endDate: string;
  quartersCovered: number;
  growthPercentage: number;
  relevantQuotes: string[];
  growthTrends: string[];
  confidence: number;
}

function formatEmbeddingForPostgres(embedding: number[]): string {
  return `[${embedding.join(",")}]`;
}

/**
 * @readonly Analyzes company growth trends from earnings call transcripts and price data across quarters
 */
export async function analyzeCompanyGrowth(
  stockSymbol: string,
  startDate: string,
  endDate: string,
  growthPercentage: number
): Promise<GrowthAnalysis> {
  console.log(
    `Starting analysis for ${stockSymbol} from ${startDate} to ${endDate}`
  );
  try {
    // Calculate number of quarters between dates
    const start = new Date(startDate);
    const end = new Date(endDate);
    const quartersDiff = Math.ceil(
      (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24 * 91.25)
    );
    console.log(`Analyzing ${quartersDiff} quarters of data`);

    // Create embeddings for growth topics
    console.log(
      "Creating embeddings for growth topics:",
      GROWTH_ANALYSIS_TOPICS
    );
    const embeddingResponse = await openai.embeddings.create({
      model: "text-embedding-3-small",
      input: GROWTH_ANALYSIS_TOPICS.join(" "),
    });
    console.log("Successfully generated embeddings");

    const queryEmbedding = embeddingResponse.data[0].embedding;
    const formattedEmbedding = formatEmbeddingForPostgres(queryEmbedding);

    // Add these diagnostic queries before the main search
    const diagnosticQueries = [
      // Check basic transcript availability
      `
      SELECT t.id, t.stock_symbol, t.date, 
             EXISTS (SELECT 1 FROM transcript_vectors tv WHERE tv.transcript_id = t.id) as has_vectors
      FROM transcripts t 
      WHERE t.stock_symbol = $1 
        AND t.date BETWEEN $2::date AND $3::date;
      `,
      // Check vector data if it exists
      `
      SELECT t.date, 
             COUNT(tv.id) as vector_count,
             MIN(array_length(tv.content_chunk_vector, 1)) as vector_dimensions,
             AVG(1 - (tv.content_chunk_vector <=> $4::vector)) as avg_similarity
      FROM transcripts t
      JOIN transcript_vectors tv ON t.id = tv.transcript_id
      WHERE t.stock_symbol = $1 
        AND t.date BETWEEN $2::date AND $3::date
      GROUP BY t.date;
      `,
      // Sample some actual content
      `
      SELECT t.date, tv.content_chunk, 
             1 - (tv.content_chunk_vector <=> $4::vector) as similarity
      FROM transcripts t
      JOIN transcript_vectors tv ON t.id = tv.transcript_id
      WHERE t.stock_symbol = $1 
        AND t.date BETWEEN $2::date AND $3::date
      LIMIT 5;
      `,
    ];

    for (let i = 0; i < diagnosticQueries.length; i++) {
      console.log(`Running diagnostic query ${i + 1}...`);
      try {
        const result = await pool.query(diagnosticQueries[i], [
          stockSymbol,
          startDate,
          endDate,
          formattedEmbedding,
        ]);
        console.log(
          `Diagnostic ${i + 1} results:`,
          JSON.stringify(result.rows, null, 2)
        );
      } catch (err) {
        console.error(`Error in diagnostic query ${i + 1}:`, err);
      }
    }

    // Modify the main search query to be more lenient
    const searchQuery = `
      WITH relevant_transcripts AS (
        SELECT t.id, t.stock_symbol, t.date
        FROM transcripts t
        WHERE t.stock_symbol = $1
          AND t.date BETWEEN $2::date AND $3::date
      )
      SELECT 
        rt.stock_symbol,
        rt.date,
        tv.content_chunk,
        1 - (tv.content_chunk_vector <=> $4::vector) as similarity
      FROM relevant_transcripts rt
      JOIN transcript_vectors tv ON rt.id = tv.transcript_id
      -- Remove similarity threshold completely for testing
      ORDER BY similarity DESC
      LIMIT 20;
    `;

    console.log("Executing transcript search query...");
    const result = await pool.query(searchQuery, [
      stockSymbol,
      startDate,
      endDate,
      formattedEmbedding,
    ]);
    console.log(`Found ${result.rows.length} relevant transcript chunks`);

    // Process results
    const relevantQuotes = result.rows.map((row) => ({
      date: row.date,
      content: row.content_chunk,
      similarity: row.similarity || 0,
    }));

    // If no relevant quotes found, return a base response
    if (relevantQuotes.length === 0) {
      console.log("No relevant quotes found in transcripts");
      return {
        stockSymbol,
        startDate,
        endDate,
        quartersCovered: quartersDiff,
        growthPercentage,
        relevantQuotes: [],
        growthTrends: [],
        confidence: 0,
      };
    }

    // Log found quotes
    console.log("Found relevant quotes:");
    relevantQuotes.forEach((quote, idx) => {
      console.log(
        `Quote ${idx + 1} [${
          quote.date
        }] (similarity: ${quote.similarity.toFixed(3)})`
      );
      console.log(quote.content.substring(0, 100) + "...");
    });

    // Analyze growth trends using OpenAI
    console.log("Analyzing growth trends with OpenAI...");
    const analysisPrompt = `Analyze these earnings call excerpts for ${stockSymbol} between ${startDate} and ${endDate} (${quartersDiff} quarters). 
The stock ${growthPercentage > 0 ? "grew" : "declined"} by ${Math.abs(
      growthPercentage
    ).toFixed(2)}% over this period.

Identify and explain key growth trends across these ${quartersDiff} quarters:
${relevantQuotes.map((q) => `[${q.date}]: ${q.content}`).join("\n\n")}`;

    const analysis = await openai.chat.completions.create({
      model: "gpt-4",
      messages: [
        {
          role: "user",
          content: analysisPrompt,
        },
      ],
      temperature: 0.3,
    });

    const trends =
      analysis.choices[0].message.content
        ?.split("\n")
        .filter((t) => t.length > 0) || [];

    console.log(`Generated ${trends.length} growth trends`);

    // Calculate confidence
    const confidence = Math.max(
      0,
      Math.min(
        1,
        relevantQuotes.reduce((acc, q) => acc + (q.similarity || 0), 0) /
          Math.max(1, relevantQuotes.length)
      )
    );
    console.log(`Analysis confidence: ${confidence.toFixed(3)}`);

    return {
      stockSymbol,
      startDate,
      endDate,
      quartersCovered: quartersDiff,
      growthPercentage,
      relevantQuotes: relevantQuotes.map((q) => q.content),
      growthTrends: trends,
      confidence,
    };
  } catch (error) {
    console.error("Error in growth analysis:", error);
    if (error instanceof Error) {
      console.error("Error details:", error.message);
      console.error("Stack trace:", error.stack);
    }
    return {
      stockSymbol,
      startDate,
      endDate,
      quartersCovered: 0,
      growthPercentage,
      relevantQuotes: [],
      growthTrends: [],
      confidence: 0,
    };
  }
}
