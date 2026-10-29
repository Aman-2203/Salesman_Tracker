from app import create_app

app = create_app()

if __name__ == '__main__':
    print('Starting TraceIt - Field Sales Tracker...')
    print('   URL: http://localhost:5000')
    print('   Admin: admin@salesforce.com / admin123 (after seeding)')
    app.run(debug=True, host='0.0.0.0', port=5000)

