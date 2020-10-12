import pandas as pd 
import numpy as np
import json
import plotly.express as px  
import plotly.graph_objects as go
import dash  
import dash_core_components as dcc
from plotly.subplots import make_subplots
import dash_html_components as html
from dash.dependencies import Input, Output
from datetime import datetime

app = dash.Dash(__name__)

def create_data_density(dep_pop_file,dep_sup_file):
    dep_sup = pd.read_csv(dep_sup_file,dtype={'dep': str, 'code': str, 'Superficie(km2)': float})
    dep_pop = pd.read_csv(dep_pop_file,dtype={'dep': str, 'code': str, 'Population(milliers)': float})
    dep_sup = dep_sup.sort_values(by=['code'])
    dep_pop['Population(milliers)'] = dep_pop['Population(milliers)'] * 1000
    dep_sup['Population(hab)'] = (dep_pop['Population(milliers)'].values)
    dep_sup['Density(hab/km2)'] =round(dep_sup['Population(hab)']/dep_sup['Superficie(km2)'],2)
    dep_sup['Density(hab/km2)_log'] = np.log10(dep_sup['Density(hab/km2)'])
    return dep_sup


def create_data_covid(covid_file,dep_pop_file,dep_sup_file): 
    data= create_data_density(dep_pop_file,dep_sup_file)
    covid = pd.read_csv(covid_file)
    covid = pd.merge(data, covid, on = ['code'])
    for i in ['974','973','972','971']: 
        covid= covid.drop(covid[ covid['code'] ==i].index, axis=0)
    covid['sum']= covid['hosp'] + covid['rea']
    covid['sum']=covid['sum'].astype('float64')
    for i in range(len(covid['sum'])): 
        if np.log(covid['sum'][i])==float('-inf'):
            covid['sum'][i]=1
    covid['jour'] =pd.to_datetime(covid['jour']).dt.date
    covid = covid.set_index('jour') 
    return covid

def getmarksDict():
    d2={}
    for i in days:
        tmp = days[i].split('-')
        if tmp[2] =='01': 
            d2[i]= mois[tmp[1]]
    return d2

def transform(date): 
    tmp = date.split('-')
    s = tmp[2] +' '+mois[tmp[1]]+' '+tmp[0]
    return s 


colors = {
    'background': '#111111',
    'text': '#7FDBFF'
}

styleMainDiv={
  'verticalAlign':'middle',
  'textAlign': 'center',
  'backgroundColor': colors['background'],
  'position':'fixed',
  'width':'100%',
  'height':'100%',
  'top':'0px',
  'left':'0px',
  'z-index':'1000'
}

styleMainTitle={'text-align': 'center',
                'color':'white'}

# ------------------------------------------------------------------------------
# Import and clean data (importing csv into pandas)
covid = create_data_covid("Data/donnees-hospitalieres-covid.csv","Data/dep-pop.csv","Data/dep-sup.csv")
france = json.load(open("Geojson/france_dep.geojson",'r'))

# ------------------------------------------------------------------------------
# App layout


mois = {'01':'Janvier','02':'Février','03':'Mars','04':'Avril','05':'Mai','06':'Juin','07':'Juillet','08':'Aout','09':'Septembre','10':'Octrobre','11':'Novembre','12':'Decembre'}

days = {int(i):str(j) for i,j in zip(range(len(covid.index.unique())), covid.index.unique())}
firstMonth ={}
firstMonth = getmarksDict()


app.layout = html.Div(style=styleMainDiv,children=[

    html.H1("Web Application Dashboards with Dash", style=styleMainTitle),
    
    html.Div([dcc.Slider(
        id='slct_day',
        min=0,
        max=len(covid.index.unique())-1,
        step=1,
        marks = firstMonth,
        included=False,
        value=0,
        ),
        html.Div(id='slider-output-container')]),

    html.Div([dcc.Graph(id='subplot', figure={})]),

])


# ------------------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components
@app.callback(
   [Output(component_id='subplot', component_property='figure'),
    Output(component_id='slider-output-container', component_property='children')],
    [Input(component_id='slct_day', component_property='value')]
)
def update_graph(option_slctd):
    #d = {int(i):str(j) for i,j in zip(range(len(covid.index.unique())), covid.index.unique())}
    covid2 = covid.copy()
    covid2 = covid2[covid2['sexe']==2]
    covid2 = covid2.loc[datetime.strptime(days[option_slctd], '%Y-%m-%d').date()]
    covid2 = covid2.sort_values(by=['Density(hab/km2)'])
    
    slider_container = transform(days[option_slctd])

    fig = make_subplots(
    rows=1, cols=2,
    column_widths=[0.35, 0.65],
    horizontal_spacing=0.03,
    specs=[[{"type": "Choroplethmapbox"}, {"type": "bar"}]],
    subplot_titles=("Hospitalisation et Réanimation par département en France","Hospitalisation et Réanimation par département en France en fonction de la densité"))

    fig.add_trace(go.Bar(
        x=covid2['dep'],
        y=covid2['hosp'],
        name='Hospitalisation',
        hovertemplate ="<b> Departement : %{customdata[0]} </b><br><b> Densité : %{customdata[4]} hab/km2</b><br><b>Hospitalisation : %{customdata[7]} pers.</b>"+"<extra></extra>",
        customdata=covid2,
        marker_color='rgb(196, 102, 73)',
        showlegend =False),
        row=1, col=2)

    fig.add_trace(go.Bar(
        x=covid2['dep'],
        y=covid2['rea'],
        name='Réanimation',
        hovertemplate ="<b> Departement : %{customdata[0]} </b><br><b> Densité : %{customdata[4]} hab/km2</b><br><b>Réanimation : %{customdata[8]} pers.</b>"+"<extra></extra>",
        customdata=covid2,
        marker_color='rgb(89, 13, 31)',
        showlegend =False),
        row=1, col=2)

    fig.add_trace(go.Choroplethmapbox(geojson=france, 
                                        locations=covid2['code'],
                                        z=np.log10(covid2['sum']),
                                        customdata=covid2,
                                        showscale=False,
                                        hovertemplate ="<b> Departement : %{customdata[0]} </b><br><b> Densité : %{customdata[4]} hab/km2</b><br><b>Hospitalisation : %{customdata[7]} pers.</b><br><b>Réanimation : %{customdata[8]} pers.</b>"+"<extra></extra>",
                                        featureidkey="properties.code",                           
                                        colorscale="amp",
                                        showlegend = False,
                                        marker_opacity=0.8, 
                                        marker_line_width=0.3,
                                        name='europe_map'),
                                        row=1, col=1)

    fig.update_layout(mapbox_style="carto-positron",mapbox_zoom=4.7, mapbox_center = {"lat": 46.35, "lon": 2.55},height=800)

    fig.update_layout(barmode='relative')
    fig.update_layout(template='plotly_dark')

    return fig,slider_container

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run_server(debug=True)