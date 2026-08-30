# Tool inventory

Tool definitions are obtained from the environment, like every other AgentSim
environment:

```bash
python - <<'PY'
import benchmarks.agentdojo as agentdojo

env = next(env for env in agentdojo.list_envs() if env.suite.name == "banking")
for tool in env.available_tools():
    print(tool)
PY
```

AgentDojo's original function signature, docstring, validation, and mutation
logic are preserved. AgentSim adds descriptive policy metadata: read-like
tools are `safe`; other tools are `risky`. Tool calls and results are recorded
by the generic AgentSim trace.

## Workspace (24)

Email:

- `send_email`, `delete_email`
- `get_unread_emails`, `get_sent_emails`, `get_received_emails`, `get_draft_emails`
- `search_emails`, `search_contacts_by_name`, `search_contacts_by_email`

Calendar:

- `get_current_day`, `search_calendar_events`, `get_day_calendar_events`
- `create_calendar_event`, `cancel_calendar_event`, `reschedule_calendar_event`
- `add_calendar_event_participants`

Cloud drive:

- `append_to_file`, `search_files_by_filename`, `create_file`, `delete_file`
- `get_file_by_id`, `list_files`, `share_file`, `search_files`

## Slack (11)

- `get_channels`, `get_users_in_channel`, `read_channel_messages`, `read_inbox`
- `add_user_to_channel`, `invite_user_to_slack`, `remove_user_from_slack`
- `send_direct_message`, `send_channel_message`
- `get_webpage`, `post_webpage`

## Travel (28)

User and lodging:

- `get_user_information`
- `get_all_hotels_in_city`, `get_hotels_prices`, `get_rating_reviews_for_hotels`
- `get_hotels_address`, `reserve_hotel`

Restaurants:

- `get_all_restaurants_in_city`, `get_cuisine_type_for_restaurants`
- `get_restaurants_address`, `get_rating_reviews_for_restaurants`
- `get_dietary_restrictions_for_all_restaurants`
- `get_contact_information_for_restaurants`, `get_price_for_restaurants`
- `check_restaurant_opening_hours`, `reserve_restaurant`

Car rental:

- `get_all_car_rental_companies_in_city`, `get_car_types_available`
- `get_rating_reviews_for_car_rental`, `get_car_fuel_options`
- `get_car_rental_address`, `get_car_price_per_day`, `reserve_car_rental`

Calendar, flights, and email:

- `create_calendar_event`, `search_calendar_events`, `get_day_calendar_events`
- `cancel_calendar_event`, `get_flight_information`, `send_email`

## Banking (11)

- `get_iban`, `get_balance`, `get_most_recent_transactions`
- `get_scheduled_transactions`, `read_file`, `get_user_info`
- `send_money`, `schedule_transaction`, `update_scheduled_transaction`
- `update_password`, `update_user_info`
