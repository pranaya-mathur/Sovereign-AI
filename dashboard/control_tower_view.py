"""Control Tower View - Minimal dashboard for LLM observability.

Provides:
1. Timeline of LLM failures
2. "Why was this blocked?" drill-down
3. "Which signal fires most?" analytics

Goal: Product feel, not demo
"""

import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from persistence.audit_store import AuditStore


class ControlTowerView:
    """CLI-based control tower dashboard."""
    
    def __init__(self, db_path: str = "data/audit.db"):
        """Initialize dashboard with audit store."""
        self.store = AuditStore(db_path)
    
    def show_banner(self) -> None:
        """Display dashboard banner."""
        print("\n" + "="*70)
        print("  🏗️  LLM OBSERVABILITY CONTROL TOWER")
        print("="*70)
        print(f"  Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("="*70 + "\n")
    
    def show_summary(self, days: int = 7) -> None:
        """Show summary statistics.
        
        Args:
            days: Look back period in days
        """
        since = datetime.utcnow() - timedelta(days=days)
        summary = self.store.get_summary(since=since)
        
        print(f"📊 SUMMARY (Last {days} days)\n")
        print(f"  Total Interactions: {summary.total_verdicts}")
        
        if summary.total_verdicts == 0:
            print("  No interactions recorded yet.\n")
            return
        
        # Actions breakdown
        print(f"\n  🚨 Actions Taken:")
        print(f"    ❌ Blocked:  {summary.blocked_count:3d} "
              f"({100*summary.blocked_count/summary.total_verdicts:.1f}%)")
        print(f"    ⚠️  Warned:   {summary.warned_count:3d} "
              f"({100*summary.warned_count/summary.total_verdicts:.1f}%)")
        print(f"    ✅ Allowed:  {summary.allowed_count:3d} "
              f"({100*summary.allowed_count/summary.total_verdicts:.1f}%)")
        
        # Severity breakdown
        print(f"\n  ⚖️  Severity Distribution:")
        if summary.critical_count > 0:
            print(f"    CRITICAL: {summary.critical_count:3d} "
                  f"({100*summary.critical_count/summary.total_verdicts:.1f}%)")
        if summary.high_count > 0:
            print(f"    HIGH:     {summary.high_count:3d} "
                  f"({100*summary.high_count/summary.total_verdicts:.1f}%)")
        if summary.medium_count > 0:
            print(f"    MEDIUM:   {summary.medium_count:3d} "
                  f"({100*summary.medium_count/summary.total_verdicts:.1f}%)")
        if summary.low_count > 0:
            print(f"    LOW:      {summary.low_count:3d} "
                  f"({100*summary.low_count/summary.total_verdicts:.1f}%)")
        
        # Top failure classes
        if summary.failure_class_counts:
            print(f"\n  🔴 Top Failure Classes:")
            sorted_failures = sorted(
                summary.failure_class_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            for failure, count in sorted_failures:
                print(f"    {failure:25s} {count:3d} times")
        
        # Top signals
        if summary.most_fired_signals:
            print(f"\n  📡 Most Fired Signals:")
            sorted_signals = sorted(
                summary.most_fired_signals.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            for signal, count in sorted_signals:
                print(f"    {signal:25s} {count:3d} times")
        
        print()
    
    def show_timeline(self, days: int = 7) -> None:
        """Show failure timeline.
        
        Args:
            days: Look back period in days
        """
        timeline = self.store.get_failure_timeline(days=days)
        
        if not timeline:
            print("📈 TIMELINE: No data available\n")
            return
        
        print(f"📈 FAILURE TIMELINE (Last {days} days)\n")
        print("  Date       │ Total │ Blocked │ Warned")
        print("  ───────────┼───────┼─────────┼────────")
        
        for date, counts in sorted(timeline.items()):
            total, blocked, warned = counts
            print(f"  {date} │ {total:5d} │ {blocked:7d} │ {warned:6d}")
        
        print()
    
    def show_recent_blocks(self, limit: int = 10) -> None:
        """Show recently blocked interactions.
        
        Args:
            limit: Maximum number to show
        """
        blocked = self.store.get_blocked_interactions(limit=limit)
        
        if not blocked:
            print("❌ RECENT BLOCKS: None\n")
            return
        
        print(f"❌ RECENT BLOCKS (Last {limit})\n")
        
        for i, interaction in enumerate(blocked, 1):
            print(f"  [{i}] {interaction['timestamp']}")
            print(f"      Reason: {interaction['verdict_reason']}")
            print(f"      Severity: {interaction['verdict_severity'].upper()}")
            print(f"      Failure: {interaction['failure_class'] or 'N/A'}")
            print(f"      Prompt: {interaction['prompt'][:60]}...")
            print()
    
    def show_interaction_detail(self, interaction_id: str) -> None:
        """Show detailed view of a specific interaction.
        
        Args:
            interaction_id: Interaction ID to examine
        """
        interaction = self.store.get_interaction(interaction_id)
        
        if not interaction:
            print(f"❌ Interaction {interaction_id} not found\n")
            return
        
        print(f"\n🔍 INTERACTION DETAIL: {interaction_id}\n")
        print("="*70)
        
        # Basic info
        print(f"Timestamp: {interaction['timestamp']}")
        print(f"Model: {interaction['model']}")
        print()
        
        # Prompt
        print("PROMPT:")
        print(f"  {interaction['prompt']}")
        print()
        
        # Response
        print("RESPONSE:")
        if interaction['response_blocked']:
            print("  ❌ BLOCKED - No response delivered")
        else:
            print(f"  {interaction['response'][:200]}...")
        print()
        
        # Verdict
        print("VERDICT:")
        print(f"  Severity: {interaction['verdict_severity'].upper()}")
        print(f"  Action: {interaction['verdict_action'].upper()}")
        print(f"  Confidence: {interaction['verdict_confidence']:.2f}")
        print(f"  Reason: {interaction['verdict_reason']}")
        if interaction['failure_class']:
            print(f"  Failure Class: {interaction['failure_class']}")
        print()
        
        # Fired signals
        signals = interaction.get('fired_signals', [])
        if signals:
            print(f"FIRED SIGNALS ({len(signals)}):")
            for signal in signals:
                print(f"  🟥 {signal['signal_name']}")
                print(f"     Confidence: {signal['confidence']:.2f}")
                print(f"     {signal['explanation']}")
                print()
        else:
            print("FIRED SIGNALS: None")
            print()
        
        print("="*70 + "\n")
    
    def show_signal_analysis(self, signal_name: Optional[str] = None) -> None:
        """Show analysis of signal firing patterns.
        
        Args:
            signal_name: Specific signal to analyze (None for summary)
        """
        if signal_name:
            history = self.store.get_signal_history(signal_name, limit=20)
            
            if not history:
                print(f"📡 SIGNAL: {signal_name} - No firing history\n")
                return
            
            print(f"📡 SIGNAL ANALYSIS: {signal_name}\n")
            print(f"  Total Fires: {len(history)}")
            print()
            print("  Recent Fires:")
            print("  Time                │ Conf  │ Action │ Prompt")
            print("  ────────────────────┼───────┼────────┼─────────")
            
            for entry in history[:10]:
                time = entry['timestamp'][:19]
                conf = entry['confidence']
                action = entry['verdict_action'][:6]
                prompt = entry['prompt'][:30]
                print(f"  {time} │ {conf:.2f} │ {action:6s} │ {prompt}...")
            print()
        else:
            # Show summary of all signals
            summary = self.store.get_summary()
            
            if not summary.most_fired_signals:
                print("📡 SIGNAL ANALYSIS: No signals fired yet\n")
                return
            
            print("📡 SIGNAL ANALYSIS - All Signals\n")
            
            sorted_signals = sorted(
                summary.most_fired_signals.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            print("  Signal Name               │ Fires │ % of Total")
            print("  ──────────────────────────┼───────┼───────────")
            
            total_signals = sum(summary.most_fired_signals.values())
            for signal, count in sorted_signals:
                pct = 100 * count / total_signals
                print(f"  {signal:25s} │ {count:5d} │ {pct:5.1f}%")
            
            print()
    
    def interactive_menu(self) -> None:
        """Show interactive menu."""
        while True:
            print("\nSelect Option:")
            print("  1. Show Summary")
            print("  2. Show Timeline")
            print("  3. Show Recent Blocks")
            print("  4. Analyze Signals")
            print("  5. View Interaction Detail")
            print("  0. Exit")
            
            choice = input("\nEnter choice: ").strip()
            
            if choice == "0":
                print("\n👋 Goodbye!\n")
                break
            elif choice == "1":
                self.show_summary(days=7)
            elif choice == "2":
                self.show_timeline(days=7)
            elif choice == "3":
                self.show_recent_blocks(limit=10)
            elif choice == "4":
                self.show_signal_analysis()
            elif choice == "5":
                interaction_id = input("Enter interaction ID: ").strip()
                if interaction_id:
                    self.show_interaction_detail(interaction_id)
            else:
                print("❌ Invalid choice\n")
    
    def run(self, command: Optional[str] = None) -> None:
        """Run dashboard.
        
        Args:
            command: Specific command to run (None for interactive)
        """
        self.show_banner()
        
        if command is None:
            # Interactive mode
            self.interactive_menu()
        elif command == "summary":
            self.show_summary(days=7)
        elif command == "timeline":
            self.show_timeline(days=7)
        elif command == "blocks":
            self.show_recent_blocks(limit=10)
        elif command == "signals":
            self.show_signal_analysis()
        else:
            print(f"❌ Unknown command: {command}\n")


def main():
    """Main entry point."""
    import sys
    
    command = sys.argv[1] if len(sys.argv) > 1 else None
    
    dashboard = ControlTowerView()
    dashboard.run(command)


if __name__ == "__main__":
    main()
