class PathfinderEngine:
    """
    Determines the ideal module 'Syllabus' and weightings based on the trader's profile.
    """
    
    def get_pathways(self):
        profiles = {
            "Intraday": {
                "description": "Fast-paced trading focusing on small price movements within seconds to minutes.",
                "weights": [
                    {"subject": "Charting & Price Action", "importance": 95, "fullMark": 100},
                    {"subject": "Trading Psychology", "importance": 100, "fullMark": 100},
                    {"subject": "Execution Replay", "importance": 90, "fullMark": 100},
                    {"subject": "Options Greeks", "importance": 70, "fullMark": 100},
                    {"subject": "Stat Arb & Algo", "importance": 40, "fullMark": 100},
                    {"subject": "Macro & News", "importance": 20, "fullMark": 100},
                    {"subject": "Portfolio Heatmap", "importance": 10, "fullMark": 100}
                ],
                "guidance": "Focus heavily on the 'Trading Psychology' and 'Execution Replay' modules. Speed and emotional control are your biggest assets. You can largely ignore long-term Macro news."
            },
            "Swing": {
                "description": "Holding positions for days to weeks to capture short-to-medium term trends.",
                "weights": [
                    {"subject": "Charting & Price Action", "importance": 90, "fullMark": 100},
                    {"subject": "Macro & News", "importance": 60, "fullMark": 100},
                    {"subject": "Trading Psychology", "importance": 80, "fullMark": 100},
                    {"subject": "Portfolio Heatmap", "importance": 50, "fullMark": 100},
                    {"subject": "Execution Replay", "importance": 50, "fullMark": 100},
                    {"subject": "Options Greeks", "importance": 30, "fullMark": 100},
                    {"subject": "Stat Arb & Algo", "importance": 20, "fullMark": 100}
                ],
                "guidance": "Focus on daily/weekly charts and sector rotation. News impact is medium importance."
            },
            "Positional": {
                "description": "Holding positions for weeks to months to capture major trend movements.",
                "weights": [
                    {"subject": "Charting & Price Action", "importance": 70, "fullMark": 100},
                    {"subject": "Macro & News", "importance": 80, "fullMark": 100},
                    {"subject": "Portfolio Heatmap", "importance": 80, "fullMark": 100},
                    {"subject": "Trading Psychology", "importance": 60, "fullMark": 100},
                    {"subject": "Execution Replay", "importance": 20, "fullMark": 100},
                    {"subject": "Options Greeks", "importance": 20, "fullMark": 100},
                    {"subject": "Stat Arb & Algo", "importance": 10, "fullMark": 100}
                ],
                "guidance": "You need to combine technicals with strong macro understanding. Portfolio heatmap helps monitor broader exposure."
            },
            "Long-term Investing": {
                "description": "Holding positions for months to years, focusing on fundamentals and broad market trends.",
                "weights": [
                    {"subject": "Macro & News", "importance": 95, "fullMark": 100},
                    {"subject": "Portfolio Heatmap", "importance": 100, "fullMark": 100},
                    {"subject": "Stat Arb & Algo", "importance": 10, "fullMark": 100},
                    {"subject": "Options Greeks", "importance": 15, "fullMark": 100},
                    {"subject": "Execution Replay", "importance": 5, "fullMark": 100},
                    {"subject": "Charting & Price Action", "importance": 50, "fullMark": 100},
                    {"subject": "Trading Psychology", "importance": 60, "fullMark": 100}
                ],
                "guidance": "Your daily routine should start with the 'News & Macro Risk Radar' and 'Portfolio Heatmap'. Options and tick-by-tick charting are distractions for you."
            },
            "Futures": {
                "description": "Trading leveraged futures contracts focusing on momentum and hedging.",
                "weights": [
                    {"subject": "Charting & Price Action", "importance": 95, "fullMark": 100},
                    {"subject": "Macro & News", "importance": 80, "fullMark": 100},
                    {"subject": "Trading Psychology", "importance": 90, "fullMark": 100},
                    {"subject": "Execution Replay", "importance": 85, "fullMark": 100},
                    {"subject": "Options Greeks", "importance": 20, "fullMark": 100},
                    {"subject": "Portfolio Heatmap", "importance": 30, "fullMark": 100},
                    {"subject": "Stat Arb & Algo", "importance": 40, "fullMark": 100}
                ],
                "guidance": "Leverage requires immense psychological control and understanding of macroeconomic catalysts."
            },
            "Options": {
                "description": "Trading options contracts, focusing on volatility, Greeks, and premium collection.",
                "weights": [
                    {"subject": "Options Greeks", "importance": 100, "fullMark": 100},
                    {"subject": "Macro & News", "importance": 85, "fullMark": 100},
                    {"subject": "Portfolio Heatmap", "importance": 70, "fullMark": 100},
                    {"subject": "Trading Psychology", "importance": 80, "fullMark": 100},
                    {"subject": "Charting & Price Action", "importance": 70, "fullMark": 100},
                    {"subject": "Stat Arb & Algo", "importance": 30, "fullMark": 100},
                    {"subject": "Execution Replay", "importance": 40, "fullMark": 100}
                ],
                "guidance": "You live in the 'Options Explorer' and 'Strategy Builder'. Use the 'Risk Radar' to ensure no flash crashes wipe out your positions."
            },
            "Equity Delivery": {
                "description": "Buying stocks for cash delivery without leverage.",
                "weights": [
                    {"subject": "Charting & Price Action", "importance": 60, "fullMark": 100},
                    {"subject": "Macro & News", "importance": 90, "fullMark": 100},
                    {"subject": "Portfolio Heatmap", "importance": 100, "fullMark": 100},
                    {"subject": "Trading Psychology", "importance": 50, "fullMark": 100},
                    {"subject": "Execution Replay", "importance": 10, "fullMark": 100},
                    {"subject": "Options Greeks", "importance": 0, "fullMark": 100},
                    {"subject": "Stat Arb & Algo", "importance": 10, "fullMark": 100}
                ],
                "guidance": "Focus strictly on fundamentals and overall portfolio diversification."
            },
            "Commodity": {
                "description": "Trading physical goods like gold, crude oil, and agriculture products.",
                "weights": [
                    {"subject": "Macro & News", "importance": 100, "fullMark": 100},
                    {"subject": "Charting & Price Action", "importance": 85, "fullMark": 100},
                    {"subject": "Trading Psychology", "importance": 80, "fullMark": 100},
                    {"subject": "Portfolio Heatmap", "importance": 40, "fullMark": 100},
                    {"subject": "Execution Replay", "importance": 60, "fullMark": 100},
                    {"subject": "Options Greeks", "importance": 10, "fullMark": 100},
                    {"subject": "Stat Arb & Algo", "importance": 20, "fullMark": 100}
                ],
                "guidance": "Commodities are highly driven by global news, geopolitics, and inventory data. Macro is your absolute priority."
            },
            "Currency": {
                "description": "Trading forex pairs based on central bank policies and global economics.",
                "weights": [
                    {"subject": "Macro & News", "importance": 100, "fullMark": 100},
                    {"subject": "Charting & Price Action", "importance": 80, "fullMark": 100},
                    {"subject": "Trading Psychology", "importance": 80, "fullMark": 100},
                    {"subject": "Portfolio Heatmap", "importance": 20, "fullMark": 100},
                    {"subject": "Execution Replay", "importance": 60, "fullMark": 100},
                    {"subject": "Options Greeks", "importance": 10, "fullMark": 100},
                    {"subject": "Stat Arb & Algo", "importance": 50, "fullMark": 100}
                ],
                "guidance": "Currencies trend based on interest rates and inflation data. Focus heavily on the Macro & News."
            },
            "Quant / Algo Developer": {
                "description": "Building automated systems using math, statistics, and code to remove human emotion.",
                "weights": [
                    {"subject": "Stat Arb & Algo", "importance": 100, "fullMark": 100},
                    {"subject": "Execution Replay", "importance": 90, "fullMark": 100},
                    {"subject": "Options Greeks", "importance": 80, "fullMark": 100},
                    {"subject": "Macro & News", "importance": 60, "fullMark": 100},
                    {"subject": "Portfolio Heatmap", "importance": 50, "fullMark": 100},
                    {"subject": "Charting & Price Action", "importance": 20, "fullMark": 100},
                    {"subject": "Trading Psychology", "importance": 10, "fullMark": 100}
                ],
                "guidance": "Your focus is purely on the 'Stat Arb Dashboard' and 'Backtesting/Replay'. Since the machine trades for you, manual charting and human psychology modules have low importance."
            }
        }
        return profiles
