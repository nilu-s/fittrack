#!/usr/bin/env python3
"""FitTrack CLI — command-line interface for the FitTrack PWA.

Usage:
    fittrack today                         # Show today's data
    fittrack day 2026-08-19                # Show specific day
    fittrack log-weight 112.5              # Log weight
    fittrack log-steps 8234                # Log steps
    fittrack log-cardio 40                 # Log cardio minutes
    fittrack log-sleep 7.5                 # Log sleep hours
    fittrack log-training "Oberkörper B"   # Set training type
    fittrack check-creatine                # Mark creatine done
    fittrack note "Good day"               # Add note
    fittrack meals                          # Show today's meals
    fittrack meal 2 --done                  # Mark meal 2 done
    fittrack todos                          # List open todos
    fittrack todo "Buy groceries"           # Create todo
    fittrack todo-done <id>                 # Mark todo done
    fittrack week                           # Week summary
    fittrack training                       # Show today's training
    fittrack training --done                # Complete training
    fittrack exercises --type "Oberkörper A"  # Show exercises
    fittrack sync                           # Trigger sync
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta
from typing import Any

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON

console = Console()

# API base URL: localhost for CLI (no auth needed)
API_BASE = os.environ.get("FITTRACK_API_URL", "http://localhost:8000/api")


def api_get(path: str, **params) -> Any:
    """Make a GET request to the API."""
    try:
        resp = httpx.get(f"{API_BASE}{path}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        console.print(f"[red]Error: Cannot connect to {API_BASE}[/red]")
        console.print("[yellow]Is the FitTrack API running? Try: docker compose up -d fittrack-api[/yellow]")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]API error {e.response.status_code}: {e.response.text}[/red]")
        sys.exit(1)


def api_post(path: str, **data) -> Any:
    """Make a POST request to the API."""
    try:
        resp = httpx.post(f"{API_BASE}{path}", json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        console.print(f"[red]Error: Cannot connect to {API_BASE}[/red]")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]API error {e.response.status_code}: {e.response.text}[/red]")
        sys.exit(1)


def api_put(path: str, **data) -> Any:
    """Make a PUT request to the API."""
    try:
        resp = httpx.put(f"{API_BASE}{path}", json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        console.print(f"[red]Error: Cannot connect to {API_BASE}[/red]")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]API error {e.response.status_code}: {e.response.text}[/red]")
        sys.exit(1)


def api_delete(path: str) -> Any:
    """Make a DELETE request to the API."""
    try:
        resp = httpx.delete(f"{API_BASE}{path}", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        console.print(f"[red]Error: Cannot connect to {API_BASE}[/red]")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]API error {e.response.status_code}: {e.response.text}[/red]")
        sys.exit(1)


def today_str() -> str:
    return date.today().isoformat()


def fmt_date(d: str) -> str:
    """Format ISO date to German display."""
    try:
        dt = datetime.fromisoformat(d)
        return dt.strftime("%a, %d.%m.%Y")
    except Exception:
        return d


def print_json(data: Any):
    """Print data as JSON (for machine reading)."""
    print(json.dumps(data, ensure_ascii=False, default=str, indent=2))


def print_day_table(data: dict):
    """Print day entry as a rich table."""
    table = Table(title=f"📊 {fmt_date(data.get('date', '???'))}", show_header=False)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    rows = [
        ("Gewicht", f"{data.get('weight_kg', '—')} kg" if data.get('weight_kg') else "— kg"),
        ("Schritte", f"{data.get('steps', '—')}/10.000" if data.get('steps') else "—"),
        ("Schlaf", f"{data.get('sleep_hours', '—')} h" if data.get('sleep_hours') else "— h"),
        ("Cardio", f"{data.get('cardio_minutes', '—')} min" if data.get('cardio_minutes') else "— min"),
        ("Training", data.get('training_type', '—') or '—'),
        ("Training Done", "✅" if data.get('training_done') else "☐"),
        ("Kreatin", "✅" if data.get('creatine_done') else "☐"),
        ("Bauch", f"{data.get('belly_cm', '—')} cm" if data.get('belly_cm') else "— cm"),
        ("Notizen", data.get('notes', '—') or '—'),
    ]

    for label, value in rows:
        table.add_row(label, str(value))

    console.print(table)


def print_meals_table(meals: list):
    """Print meals as a table."""
    table = Table(title="🍽️ Mahlzeiten", show_header=True)
    table.add_column("Slot", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("kcal", justify="right", style="yellow")
    table.add_column("P", justify="right", style="blue")
    table.add_column("KH", justify="right", style="magenta")
    table.add_column("F", justify="right", style="red")
    table.add_column("Done", justify="center")

    total_kcal = 0
    total_p = 0
    total_kh = 0
    total_f = 0

    for meal in meals:
        kcal = float(meal.get('kcal') or 0)
        p = float(meal.get('protein_g') or 0)
        kh = float(meal.get('carbs_g') or 0)
        f = float(meal.get('fat_g') or 0)
        total_kcal += kcal
        total_p += p
        total_kh += kh
        total_f += f
        done = "✅" if meal.get('is_done') else "☐"
        table.add_row(
            str(meal.get('meal_slot', '?')),
            meal.get('name', '—'),
            f"{kcal:.0f}",
            f"{p:.0f}g",
            f"{kh:.0f}g",
            f"{f:.0f}g",
            done,
        )

    table.add_row("Σ", "Total", f"{total_kcal:.0f}", f"{total_p:.0f}g", f"{total_kh:.0f}g", f"{total_f:.0f}g", "")
    console.print(table)


def print_todos_table(todos: list):
    """Print todos as a table."""
    if not todos:
        console.print("[yellow]Keine To-Dos gefunden.[/yellow]")
        return

    table = Table(title="📋 To-Dos", show_header=True)
    table.add_column("ID", style="dim", width=8)
    table.add_column("Status", justify="center", width=4)
    table.add_column("Title", style="white")
    table.add_column("Cat", style="cyan", width=8)
    table.add_column("Pri", justify="center", width=3)
    table.add_column("Due", style="green", width=12)
    table.add_column("Time", style="green", width=8)

    for todo in todos:
        status = "✅" if todo.get('status') == 'done' else "☐"
        pri = f"P{todo.get('priority', 2)}"
        due = todo.get('due_date') or '—'
        time_val = todo.get('start_time') or todo.get('due_time') or '—'
        if due != '—':
            try:
                due = datetime.fromisoformat(due).strftime('%d.%m')
            except Exception:
                pass

        cat = todo.get('category') or '—'
        cal_badge = "📅" if todo.get('source') == 'google_calendar' else ""

        table.add_row(
            str(todo.get('id', ''))[:8],
            status,
            f"{cal_badge} {todo.get('title', '')}",
            cat,
            pri,
            due,
            str(time_val),
        )

    console.print(table)


def print_training_table(data: dict):
    """Print training data as a table."""
    training_type = data.get('training_type', '—')
    console.print(Panel(f"🏋️ Training: [bold]{training_type}[/bold]", style="blue"))

    exercises = data.get('exercises', [])
    if not exercises:
        console.print("[yellow]Keine Übungen für diesen Trainingstyp.[/yellow]")
        return

    table = Table(show_header=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Übung", style="white")
    table.add_column("Sätze", style="cyan")
    table.add_column("Reps", justify="right")
    table.add_column("kg", justify="right", style="yellow")
    table.add_column("RIR", justify="center")
    table.add_column("Topset", justify="center")

    for i, ex in enumerate(exercises, 1):
        reps = f"{ex.get('target_reps_low', '?')}-{ex.get('target_reps_high', '?')}"
        weight = f"{float(ex.get('target_weight_kg') or 0):.1f}" if ex.get('target_weight_kg') else "—"
        rir = str(ex.get('target_rir', '—'))
        topset = "✅" if ex.get('is_topset') else ""
        table.add_row(
            str(i),
            ex.get('exercise_name', '—'),
            ex.get('target_sets', '—'),
            reps,
            weight,
            rir,
            topset,
        )

    console.print(table)


def print_week_table(data: dict):
    """Print week summary."""
    console.print(Panel("📈 Wochenübersicht", style="green"))

    table = Table(show_header=False)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    rows = [
        ("Ø Gewicht", f"{data.get('avg_weight', '—')} kg"),
        ("Ø Kalorien", f"{data.get('avg_kcal', '—')} kcal"),
        ("Ø Schritte", f"{data.get('avg_steps', '—')}"),
        ("Ø Schlaf", f"{data.get('avg_sleep', '—')} h"),
        ("Trainingstage", f"{data.get('training_days', '—')}"),
        ("To-Dos erledigt", f"{data.get('todo_completion', '—')} %"),
        ("Tage im Cut", f"{data.get('days_in_cut', '—')}"),
        ("Veränderung", f"{data.get('weight_change', '—')} kg"),
    ]

    for label, value in rows:
        table.add_row(label, str(value))

    console.print(table)


@click.group()
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
@click.pass_context
def cli(ctx, output_json):
    """FitTrack CLI — Fitness & Todo tracking from terminal."""
    ctx.ensure_object(dict)
    ctx.obj['json'] = output_json


@cli.command()
@click.pass_context
def today(ctx):
    """Show today's data."""
    data = api_get('/day-entries', date=today_str())
    if ctx.obj.get('json'):
        print_json(data)
    else:
        print_day_table(data)

    # Also fetch meals and todos
    try:
        meals = api_get('/meals', date=today_str())
        if ctx.obj.get('json'):
            print_json(meals)
        else:
            print_meals_table(meals)
    except Exception:
        pass

    try:
        todos = api_get('/todos', date=today_str(), status='open')
        if ctx.obj.get('json'):
            print_json(todos)
        else:
            print_todos_table(todos)
    except Exception:
        pass


@cli.command()
@click.argument('date_str')
@click.pass_context
def day(ctx, date_str):
    """Show data for a specific date (YYYY-MM-DD)."""
    data = api_get('/day-entries', date=date_str)
    if ctx.obj.get('json'):
        print_json(data)
    else:
        print_day_table(data)

    try:
        meals = api_get('/meals', date=date_str)
        print_meals_table(meals)
    except Exception:
        pass

    try:
        todos = api_get('/todos', date=date_str, status='open')
        print_todos_table(todos)
    except Exception:
        pass


@cli.command(name='log-weight')
@click.argument('weight', type=float)
@click.pass_context
def log_weight(ctx, weight):
    """Log today's weight in kg."""
    data = api_put('/day-entries', date=today_str(), weight_kg=weight)
    if ctx.obj.get('json'):
        print_json(data)
    else:
        console.print(f"[green]✅ Gewicht eingetragen: {weight} kg[/green]")


@cli.command(name='log-steps')
@click.argument('steps', type=int)
@click.pass_context
def log_steps(ctx, steps):
    """Log today's steps."""
    data = api_put('/day-entries', date=today_str(), steps=steps)
    if ctx.obj.get('json'):
        print_json(data)
    else:
        console.print(f"[green]✅ Schritte eingetragen: {steps}[/green]")


@cli.command(name='log-cardio')
@click.argument('minutes', type=int)
@click.pass_context
def log_cardio(ctx, minutes):
    """Log today's cardio minutes."""
    data = api_put('/day-entries', date=today_str(), cardio_minutes=minutes)
    if ctx.obj.get('json'):
        print_json(data)
    else:
        console.print(f"[green]✅ Cardio eingetragen: {minutes} min[/green]")


@cli.command(name='log-sleep')
@click.argument('hours', type=float)
@click.pass_context
def log_sleep(ctx, hours):
    """Log today's sleep hours."""
    data = api_put('/day-entries', date=today_str(), sleep_hours=hours)
    if ctx.obj.get('json'):
        print_json(data)
    else:
        console.print(f"[green]✅ Schlaf eingetragen: {hours} h[/green]")


@cli.command(name='log-training')
@click.argument('training_type')
@click.pass_context
def log_training(ctx, training_type):
    """Set today's training type."""
    data = api_put('/day-entries', date=today_str(), training_type=training_type)
    if ctx.obj.get('json'):
        print_json(data)
    else:
        console.print(f"[green]✅ Training gesetzt: {training_type}[/green]")


@cli.command(name='check-creatine')
@click.pass_context
def check_creatine(ctx):
    """Mark creatine as done today."""
    data = api_put('/day-entries', date=today_str(), creatine_done=True)
    if ctx.obj.get('json'):
        print_json(data)
    else:
        console.print("[green]✅ Kreatin abgehakt[/green]")


@cli.command()
@click.argument('text')
@click.pass_context
def note(ctx, text):
    """Add a note to today."""
    data = api_put('/day-entries', date=today_str(), notes=text)
    if ctx.obj.get('json'):
        print_json(data)
    else:
        console.print(f"[green]✅ Notiz hinzugefügt: {text}[/green]")


@cli.command()
@click.pass_context
def meals(ctx):
    """Show today's meals."""
    data = api_get('/meals', date=today_str())
    if ctx.obj.get('json'):
        print_json(data)
    else:
        print_meals_table(data)


@cli.command()
@click.argument('slot', type=int)
@click.option('--done', is_flag=True, help='Mark meal as done')
@click.option('--replace', type=str, help='Replace meal name')
@click.option('--kcal', type=float, help='Set kcal')
@click.option('--protein', type=float, help='Set protein g')
@click.option('--carbs', type=float, help='Set carbs g')
@click.option('--fat', type=float, help='Set fat g')
@click.pass_context
def meal(ctx, slot, done, replace, kcal, protein, carbs, fat):
    """Manage a meal by slot (1-4)."""
    meals_data = api_get('/meals', date=today_str())
    target = None
    for m in meals_data:
        if m.get('meal_slot') == slot:
            target = m
            break

    if not target:
        console.print(f"[red]Mahlzeit Slot {slot} nicht gefunden[/red]")
        sys.exit(1)

    meal_id = target['id']

    if done:
        api_post(f'/meals/{meal_id}/done')
        console.print(f"[green]✅ Mahlzeit {slot} abgehakt[/green]")
    elif replace or kcal or protein or carbs or fat:
        update_data = {}
        if replace:
            update_data['name'] = replace
            update_data['is_standard'] = False
        if kcal:
            update_data['kcal'] = kcal
        if protein:
            update_data['protein_g'] = protein
        if carbs:
            update_data['carbs_g'] = carbs
        if fat:
            update_data['fat_g'] = fat
        api_put(f'/meals/{meal_id}', **update_data)
        console.print(f"[green]✅ Mahlzeit {slot} aktualisiert[/green]")
    else:
        if ctx.obj.get('json'):
            print_json(target)
        else:
            print_meals_table([target])


@cli.command()
@click.option('--status', type=str, default='open', help='Filter: open/done/all')
@click.option('--category', type=str, help='Filter by category')
@click.option('--sort', type=str, default='time', help='Sort: time/priority/due')
@click.pass_context
def todos(ctx, status, category, sort):
    """List todos."""
    params = {'date': today_str(), 'status': status}
    if category:
        params['category'] = category
    if sort:
        params['sort'] = sort
    data = api_get('/todos', **params)
    if ctx.obj.get('json'):
        print_json(data)
    else:
        print_todos_table(data)


@cli.command()
@click.argument('title')
@click.option('--priority', type=int, default=2, help='Priority 1-4')
@click.option('--category', type=str, default='personal', help='Category')
@click.option('--due', type=str, help='Due date YYYY-MM-DD')
@click.option('--time', 'due_time', type=str, help='Due time HH:MM')
@click.pass_context
def todo(ctx, title, priority, category, due, due_time):
    """Create a new todo."""
    data = {
        'title': title,
        'priority': priority,
        'category': category,
    }
    if due:
        data['due_date'] = due
    if due_time:
        data['due_time'] = due_time
        data['is_all_day'] = False

    result = api_post('/todos', **data)
    if ctx.obj.get('json'):
        print_json(result)
    else:
        console.print(f"[green]✅ To-Do erstellt: {title}[/green]")
        console.print(f"[dim]ID: {result.get('id', '???')}[/dim]")


@cli.command(name='todo-done')
@click.argument('todo_id')
@click.pass_context
def todo_done(ctx, todo_id):
    """Mark a todo as done."""
    api_post(f'/todos/{todo_id}/done')
    if ctx.obj.get('json'):
        print_json({'status': 'done', 'id': todo_id})
    else:
        console.print(f"[green]✅ To-Do abgehakt: {todo_id}[/green]")


@cli.command(name='todo-delete')
@click.argument('todo_id')
@click.pass_context
def todo_delete(ctx, todo_id):
    """Delete a todo."""
    api_delete(f'/todos/{todo_id}')
    if ctx.obj.get('json'):
        print_json({'status': 'deleted', 'id': todo_id})
    else:
        console.print(f"[green]🗑️ To-Do gelöscht: {todo_id}[/green]")


@cli.command()
@click.pass_context
def week(ctx):
    """Show week summary."""
    data = api_get('/stats/week', date=today_str())
    if ctx.obj.get('json'):
        print_json(data)
    else:
        print_week_table(data)


@cli.command()
@click.pass_context
def training(ctx):
    """Show today's training (with progressed values)."""
    data = api_get('/training', date=today_str())
    if ctx.obj.get('json'):
        print_json(data)
    else:
        print_training_table(data)


@cli.command()
@click.option('--done', is_flag=True, help='Complete training (save sets + progress)')
@click.option('--next', 'next_type', type=str, help='Show next training of this type')
@click.option('--log-set', 'log_exercise', type=str, help='Log a set: exercise name')
@click.option('--set', 'set_num', type=int, help='Set number')
@click.option('--reps', type=int, help='Reps achieved')
@click.option('--weight', type=float, help='Weight in kg')
@click.option('--rir', type=int, help='RIR (Reps in Reserve)')
@click.pass_context
def training(ctx, done, next_type, log_exercise, set_num, reps, weight, rir):
    """Training management."""
    if next_type:
        data = api_get('/training/next', training_type=next_type)
        if ctx.obj.get('json'):
            print_json(data)
        else:
            print_training_table(data)
    elif done:
        # Complete today's training
        training_data = api_get('/training', date=today_str())
        training_type = training_data.get('training_type')

        if log_exercise:
            # Log a single set then complete
            sets_data = [{
                'exercise_name': log_exercise,
                'set_number': set_num or 1,
                'reps': reps or 0,
                'weight_kg': weight or 0,
                'rir': rir or 2,
                'set_type': 'work',
            }]
        else:
            # Just complete with whatever exercises are configured
            sets_data = []

        result = api_post('/training/complete', date=today_str(), training_type=training_type, sets=sets_data)
        if ctx.obj.get('json'):
            print_json(result)
        else:
            console.print(f"[green]✅ Training abgeschlossen: {training_type}[/green]")
            if result.get('next_training'):
                console.print(f"[blue]Nächstes Mal: {result['next_training'].get('training_type')}[/blue]")
    else:
        data = api_get('/training', date=today_str())
        if ctx.obj.get('json'):
            print_json(data)
        else:
            print_training_table(data)


@cli.command()
@click.option('--type', 'training_type', type=str, help='Filter by training type')
@click.option('--add', 'add_name', type=str, help='Add new exercise')
@click.option('--sets', type=str, help='Target sets (e.g. "3×8-12")')
@click.option('--reps-low', type=int, help='Low rep range')
@click.option('--reps-high', type=int, help='High rep range')
@click.option('--weight', type=float, help='Target weight kg')
@click.option('--progression', type=str, default='double_progression', help='Progression strategy')
@click.pass_context
def exercises(ctx, training_type, add_name, sets, reps_low, reps_high, weight, progression):
    """Show or add exercises."""
    if add_name:
        if not training_type:
            console.print("[red]--type required when adding exercise[/red]")
            sys.exit(1)
        data = api_post('/exercises',
            training_type=training_type,
            exercise_name=add_name,
            target_sets=sets or '3×8-12',
            target_reps_low=reps_low or 8,
            target_reps_high=reps_high or 12,
            target_weight_kg=weight,
            progression_strategy=progression,
        )
        if ctx.obj.get('json'):
            print_json(data)
        else:
            console.print(f"[green]✅ Übung hinzugefügt: {add_name}[/green]")
    elif training_type:
        data = api_get('/exercises', training_type=training_type)
        if ctx.obj.get('json'):
            print_json(data)
        else:
            console.print(Panel(f"🏋️ Übungen: {training_type}", style="blue"))
            table = Table(show_header=True)
            table.add_column("#", width=3)
            table.add_column("Übung", style="white")
            table.add_column("Sätze", style="cyan")
            table.add_column("Reps")
            table.add_column("kg", justify="right")
            table.add_column("RIR", justify="center")
            for i, ex in enumerate(data, 1):
                reps = f"{ex.get('target_reps_low', '?')}-{ex.get('target_reps_high', '?')}"
                w = f"{float(ex.get('target_weight_kg') or 0):.1f}" if ex.get('target_weight_kg') else "—"
                table.add_row(str(i), ex.get('exercise_name', ''), ex.get('target_sets', ''),
                             reps, w, str(ex.get('target_rir', '—')))
            console.print(table)
    else:
        # List all exercises grouped by type
        for t in ['Oberkörper A', 'Unterkörper A', 'Oberkörper B', 'Unterkörper B']:
            try:
                data = api_get('/exercises', training_type=t)
                console.print(Panel(f"🏋️ {t}", style="blue"))
                table = Table(show_header=True)
                table.add_column("#", width=3)
                table.add_column("Übung", style="white")
                table.add_column("Sätze", style="cyan")
                table.add_column("Reps")
                table.add_column("kg", justify="right")
                table.add_column("RIR", justify="center")
                for i, ex in enumerate(data, 1):
                    reps = f"{ex.get('target_reps_low', '?')}-{ex.get('target_reps_high', '?')}"
                    w = f"{float(ex.get('target_weight_kg') or 0):.1f}" if ex.get('target_weight_kg') else "—"
                    table.add_row(str(i), ex.get('exercise_name', ''), ex.get('target_sets', ''),
                                 reps, w, str(ex.get('target_rir', '—')))
                console.print(table)
            except Exception:
                pass


@cli.command()
@click.pass_context
def sync(ctx):
    """Trigger a manual sync."""
    data = api_post('/sync', last_sync=datetime.now().isoformat(), changes=[], client_id='cli')
    if ctx.obj.get('json'):
        print_json(data)
    else:
        console.print(f"[green]✅ Sync abgeschlossen[/green]")
        console.print(f"[dim]Server changes: {len(data.get('server_changes', []))}[/dim]")


@cli.command(name='sync-status')
@click.pass_context
def sync_status(ctx):
    """Show sync status."""
    data = api_get('/health')
    if ctx.obj.get('json'):
        print_json(data)
    else:
        console.print(f"[green]API Status: {data.get('status', '???')}[/green]")


@cli.command()
@click.option('--days', type=int, default=7, help='Number of days')
@click.pass_context
def stats(ctx, days):
    """Show statistics."""
    data = api_get('/stats/trend', metric='weight', days=days)
    if ctx.obj.get('json'):
        print_json(data)
    else:
        console.print(Panel(f"📈 Gewichtstrend ({days} Tage)", style="green"))
        for entry in data:
            console.print(f"  {entry.get('date', '???')}: {entry.get('value', '—')} kg")


@cli.command(name='weight-trend')
@click.option('--days', type=int, default=30)
@click.pass_context
def weight_trend(ctx, days):
    """Show weight trend."""
    data = api_get('/stats/trend', metric='weight', days=days)
    if ctx.obj.get('json'):
        print_json(data)
    else:
        console.print(Panel(f"📈 Gewichtstrend ({days} Tage)", style="green"))
        for entry in data:
            console.print(f"  {entry.get('date', '???')}: {entry.get('value', '—')} kg")


@cli.command(name='kcal-trend')
@click.option('--days', type=int, default=14)
@click.pass_context
def kcal_trend(ctx, days):
    """Show kcal trend."""
    data = api_get('/stats/trend', metric='kcal', days=days)
    if ctx.obj.get('json'):
        print_json(data)
    else:
        console.print(Panel(f"🔥 kcal-Trend ({days} Tage)", style="yellow"))
        for entry in data:
            console.print(f"  {entry.get('date', '???')}: {entry.get('value', '—')} kcal")


def main():
    """Entry point."""
    cli()


if __name__ == '__main__':
    main()