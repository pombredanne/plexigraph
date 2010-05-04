from django.shortcuts import render_to_response, redirect, HttpResponse
from django.utils import simplejson

import networkx as nx
import pickle
from plxgraph.nx.interaction import NetworkxInteractor
from plxgraph.tools import importers

import settings
from plexigraph.graphview.models import Dataset

SCALE = settings.EXPLORER_CANVAS_SIZE


def index(request):
    datasets = Dataset.objects.all()
    request.session.pop('interactor', None)
    request.session.pop('layout', None)
    return render_to_response('graphview/index.html', {'datasets':datasets})


def explore(request, dataset_id):
    dataset = Dataset.objects.get(pk=dataset_id)
    styles = dataset.node_styles()
    interactor = request.session.get('interactor')
    interactive_mode = False
    if (not interactor):
        try:
            if dataset.data_type == 'plxgh':
                graph = importers.dictionary_to_nx(dataset.topics.path,
                                            dataset.relations.path,
                                            dataset.get_configuration())
            else:
                graph = getattr(nx, 'read_%s' % dataset.data_type)(dataset.graph_file)
        except ValueError:
            return redirect('plexigraph.graphview.views.index')
        interactor = NetworkxInteractor(graph, dataset.get_configuration())
        request.session['interactor'] = interactor
        for key in styles.keys():
            styles[key]['show'] = True
        request.session['node_styles'] = styles.copy()
    graph = interactor.get_shown_graph(request.session['node_styles'])
    if graph.number_of_nodes() < settings.MAX_INTERACTIVE_NODES:
        interactive_mode = True
    layout = request.session.get('layout')
    if (not layout and not interactive_mode):
        if not dataset.layout:
            layout = nx.drawing.spring_layout(graph, scale=SCALE)
            request.session['layout'] = layout
            dataset.layout = pickle.dumps(layout)
            dataset.save()
        else:
            layout = dataset.layout
            request.session['layout'] = layout
    nodes = {}
    edges = {}
    for node in graph.nodes():
        nodes[node] = graph.node[node].copy()
        nodes[node]['ID'] = node
        if (not interactive_mode):
            nodes[node]['xpos'] = layout[node][0]
            nodes[node]['ypos'] = layout[node][1]
        nodes[node].update(interactor.node_data(node))
        try:
            nodes[node]['color'] = styles[str(graph.node[node]['type'])]['color']
            nodes[node]['size'] = styles[str(graph.node[node]['type'])]['size']
        except KeyError:
            nodes[node]['color'] = "#ffffff"
            nodes[node]['size'] = "1.0"
    for i in range(len(graph.edges())):
        edge = graph.edges()[i]
        edges[i] = {'ID': i,
                    'node1': edge[0],
                    'node2': edge[1]}
    new_graph = {'nodes': nodes, 'edges':edges}
    metadata_list = [(key, value) for key, value 
                        in interactor.get_metadata().iteritems()]
    node_style_list = [(key,value) for key,value 
                        in request.session['node_styles'].iteritems()]
    json_graph = simplejson.dumps(new_graph)
    if interactive_mode:
        template = 'graphview/interactive_explorer.html'
    else:
        template = 'graphview/explorer.html'
    return render_to_response(template, 
                                {'json_graph':json_graph,
                                'dataset': dataset,
                                'metadata_list': metadata_list,
                                'node_style_list': node_style_list})


def delete_nodes(request, dataset_id, node_list):
    node_list = node_list.split(',')
    interactor = request.session.get('interactor')
    if interactor:
        for node_id in node_list:
            interactor.remove_nodes([node_id])
        request.session['interactor'] = interactor
    return redirect('plexigraph.graphview.views.explore', dataset_id=dataset_id)


def delete_edges(request, dataset_id, edge_list):
    edge_list = zip(*[iter(edge_list.split(','))]*2)
    interactor = request.session.get('interactor')
    if interactor:
        for edge_tuple in edge_list:
            interactor.remove_edges([edge_tuple])
        request.session['interactor'] = interactor
    return redirect('plexigraph.graphview.views.explore', dataset_id=dataset_id)


def toggle_nodes(request, dataset_id, node_type):
    styles = request.session['node_styles']
    styles[node_type]['show'] = not styles[node_type]['show']
    request.session['node_styles'] = styles
    return redirect('plexigraph.graphview.views.explore', dataset_id=dataset_id)


def relayout(request, dataset_id):
    interactor = request.session.get('interactor')
    if interactor:
        layout = nx.drawing.spring_layout(interactor.graph, scale=SCALE)
        request.session['layout'] = layout
    return redirect('plexigraph.graphview.views.explore', dataset_id=dataset_id)


def reset(request, dataset_id):
    interactor = request.session.get('interactor')
    if interactor:
        request.session.pop('interactor')
        request.session.pop('layout')
    return redirect('plexigraph.graphview.views.explore', dataset_id=dataset_id)


def save_state(request, dataset_id):
    interactor = request.session.get('interactor')
    if interactor:
        interactor.save_graph()
        request.session['interactor'] = interactor
    return redirect('plexigraph.graphview.views.explore', dataset_id=dataset_id)


def load_state(request, dataset_id):
    interactor = request.session.get('interactor')
    if interactor:
        interactor.reset_graph()
        request.session['interactor'] = interactor
        layout = nx.drawing.spring_layout(interactor.graph, scale=SCALE)
        request.session['layout'] = layout
    return redirect('plexigraph.graphview.views.explore', dataset_id=dataset_id)


def delete_isolated(request, dataset_id):
    interactor = request.session.get('interactor')
    if interactor:
        interactor.remove_isolated_nodes()
        request.session['interactor'] = interactor
    return redirect('plexigraph.graphview.views.explore', dataset_id=dataset_id)


def expand_nodes(request, dataset_id, node_list):
    node_list = node_list.split(',')
    interactor = request.session.get('interactor')
    if interactor:
        for node_id in node_list:
            interactor.expand_node([node_id])
        request.session['interactor'] = interactor
        layout = nx.drawing.spring_layout(interactor.graph, scale=SCALE)
        request.session['layout'] = layout
    return redirect('plexigraph.graphview.views.explore', dataset_id=dataset_id)


def interactor_query(request, dataset_id, query):
    interactor = request.session.get('interactor')
    if interactor:
        """
        for method in dir(interactor):
            if method == query_data[0]:
                break
        else:
            pass
        parameters = query_data[1:]
        getattr(interactor, method)(parameters)
        """
        try:
            eval(query)
            request.session['interactor'] = interactor
            if request.session.has_key('layout'):
                request.session.pop('layout')
        except:
            print "Fix me"
    return redirect('plexigraph.graphview.views.explore', dataset_id=dataset_id)
